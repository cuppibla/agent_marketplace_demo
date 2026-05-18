"""Tools for DogWalkerAgent.

Uses Application Default Credentials (ADC) + the new Maps Platform APIs
(Places API New, Routes API, Geocoding API) — no API key needed.

Each function is registered with the LlmAgent as a FunctionTool.
"""

import json
import os
from pathlib import Path

import httpx

from common.auth import get_dynamic_headers

_BUDDY_PATH = Path(__file__).parent / "buddy.json"


def _maps_headers(field_mask: str | None = None) -> dict:
    """Headers for Maps Platform API calls — ADC token + optional field mask.

    `get_dynamic_headers()` already sets x-goog-user-project from the
    credentials' quota_project_id; we ensure it's present without doubling.
    """
    headers = get_dynamic_headers()
    if "x-goog-user-project" not in {k.lower() for k in headers}:
        headers["X-Goog-User-Project"] = os.environ["GOOGLE_CLOUD_PROJECT"]
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    return headers


def get_dog_profile() -> dict:
    """Return the resident dog's profile (breed, energy, preferences, constraints).

    Use this first to learn what kind of walk fits the dog.
    """
    with open(_BUDDY_PATH) as f:
        return json.load(f)


def get_weather(location: str) -> dict:
    """Fetch current weather for a location string (city or 'lat,lon').

    Returns temperature in F, conditions, precipitation, and wind.
    Powered by wttr.in (free, no key).
    """
    url = f"https://wttr.in/{location}?format=j1"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    current = data["current_condition"][0]
    return {
        "temp_f": int(current["temp_F"]),
        "feels_like_f": int(current["FeelsLikeF"]),
        "conditions": current["weatherDesc"][0]["value"],
        "humidity_pct": int(current["humidity"]),
        "precip_mm": float(current["precipMM"]),
        "wind_mph": int(current["windspeedMiles"]),
    }


def _geocode(address: str) -> dict | None:
    """Address -> {lat, lng, formatted_address} via Places API searchText (OAuth)."""
    url = "https://places.googleapis.com/v1/places:searchText"
    field_mask = "places.id,places.formattedAddress,places.location"
    body = {"textQuery": address, "maxResultCount": 1}
    resp = httpx.post(
        url, headers=_maps_headers(field_mask), json=body, timeout=10.0
    )
    if resp.status_code >= 400:
        return None
    places = resp.json().get("places", [])
    if not places:
        return None
    first = places[0]
    loc = first.get("location", {})
    return {
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "formatted_address": first.get("formattedAddress", address),
    }


def find_dog_parks(near_address: str, radius_meters: int = 1500) -> list[dict]:
    """Find dog-friendly parks near an address.

    Returns a list of candidate parks with name, address, rating, and
    walking distance/duration from the given address. The agent reasons
    over this list to pick the best option for the dog and weather.
    """
    origin = _geocode(near_address)
    if not origin:
        return []

    # Places API (New) — searchNearby with OAuth
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.location,places.rating,places.userRatingCount"
    )
    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = {
        "includedTypes": ["dog_park", "park"],
        "maxResultCount": 8,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": origin["lat"], "longitude": origin["lng"]},
                "radius": float(radius_meters),
            }
        },
    }
    resp = httpx.post(url, headers=_maps_headers(field_mask), json=body, timeout=15.0)
    resp.raise_for_status()
    places = resp.json().get("places", [])

    # Routes API — computeRouteMatrix for walking distances
    if not places:
        return []
    destinations = [
        {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": p["location"]["latitude"],
                        "longitude": p["location"]["longitude"],
                    }
                }
            }
        }
        for p in places
    ]
    matrix_url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    matrix_body = {
        "origins": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": origin["lat"],
                            "longitude": origin["lng"],
                        }
                    }
                }
            }
        ],
        "destinations": destinations,
        "travelMode": "WALK",
    }
    matrix_mask = "originIndex,destinationIndex,duration,distanceMeters,status"
    matrix_resp = httpx.post(
        matrix_url,
        headers=_maps_headers(matrix_mask),
        json=matrix_body,
        timeout=15.0,
    )
    matrix_resp.raise_for_status()
    matrix = {row["destinationIndex"]: row for row in matrix_resp.json()}

    parks = []
    for i, p in enumerate(places):
        m = matrix.get(i, {})
        duration_str = m.get("duration", "0s").rstrip("s")
        parks.append({
            "name": p.get("displayName", {}).get("text"),
            "address": p.get("formattedAddress"),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("userRatingCount"),
            "walk_distance_m": m.get("distanceMeters"),
            "walk_duration_s": int(duration_str) if duration_str.isdigit() else None,
            "place_id": p.get("id"),
        })
    parks.sort(key=lambda x: x.get("walk_distance_m") or 999999)
    return parks


def get_walking_route(
    origin: str,
    destination: str,
    waypoints: list[str] | None = None,
) -> dict:
    """Build a walking route from origin to destination with optional waypoints.

    Returns total distance/duration, per-leg directions, and a Google Maps URL.
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    body: dict = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "WALK",
        "computeAlternativeRoutes": False,
    }
    if waypoints:
        body["intermediates"] = [{"address": w} for w in waypoints]
    field_mask = (
        "routes.duration,routes.distanceMeters,"
        "routes.legs.duration,routes.legs.distanceMeters"
    )
    resp = httpx.post(url, headers=_maps_headers(field_mask), json=body, timeout=15.0)
    if resp.status_code >= 400:
        return {"error": f"Routes API {resp.status_code}: {resp.text[:400]}", "request_body": body}
    routes = resp.json().get("routes", [])
    if not routes:
        return {"error": "No route found"}

    route = routes[0]
    legs = route.get("legs", [])

    def _seconds(d: str) -> int:
        return int(d.rstrip("s")) if d and d.rstrip("s").isdigit() else 0

    total_duration_s = _seconds(route.get("duration", "0s"))
    total_distance_m = route.get("distanceMeters", 0)

    waypoint_part = ""
    if waypoints:
        waypoint_part = "&waypoints=" + "|".join(waypoints).replace(" ", "+")
    map_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin.replace(' ', '+')}"
        f"&destination={destination.replace(' ', '+')}"
        f"&travelmode=walking{waypoint_part}"
    )

    return {
        "total_distance_m": total_distance_m,
        "total_duration_s": total_duration_s,
        "total_duration_min": round(total_duration_s / 60),
        "legs": [
            {
                "distance_m": leg.get("distanceMeters", 0),
                "duration_min": round(_seconds(leg.get("duration", "0s")) / 60),
            }
            for leg in legs
        ],
        "map_url": map_url,
    }
