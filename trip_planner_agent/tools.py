"""Tools for TripPlannerAgent — destination weather, attractions search, routes.

Uses ADC + Maps Platform APIs (no API key), same pattern as DogWalker.
"""

import os
import sys
from pathlib import Path

import httpx

# Allow `common` import when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.auth import get_dynamic_headers


def _maps_headers(field_mask: str | None = None) -> dict:
    headers = get_dynamic_headers()
    if "x-goog-user-project" not in {k.lower() for k in headers}:
        headers["X-Goog-User-Project"] = os.environ["GOOGLE_CLOUD_PROJECT"]
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    return headers


def get_weather(location: str) -> dict:
    """Fetch current weather for a city or 'lat,lon' string.

    Returns temperature in F, conditions, precipitation, wind, humidity.
    Powered by wttr.in.
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


def find_attractions(
    city: str,
    category: str = "tourist attractions",
    max_results: int = 10,
) -> list[dict]:
    """Search for points of interest in a city.

    Args:
        city: Destination city (e.g. "Kyoto, Japan").
        category: What to search for — "tourist attractions", "temples",
            "restaurants", "museums", "parks", "shopping", etc.
        max_results: 1-20.

    Returns a ranked list of places with name, address, rating, and types.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.rating,places.userRatingCount,places.types,places.location"
    )
    body = {
        "textQuery": f"{category} in {city}",
        "maxResultCount": min(max(max_results, 1), 20),
    }
    resp = httpx.post(
        url, headers=_maps_headers(field_mask), json=body, timeout=15.0
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])
    return [
        {
            "name": p.get("displayName", {}).get("text"),
            "address": p.get("formattedAddress"),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("userRatingCount"),
            "types": p.get("types", [])[:5],
            "place_id": p.get("id"),
        }
        for p in places
    ]


def get_walking_route(
    origin: str,
    destination: str,
    waypoints: list[str] | None = None,
) -> dict:
    """Build a walking route from origin to destination with optional waypoints.

    Returns total distance/duration, per-leg breakdown, and a Google Maps URL.
    Use this to estimate walking time between trip stops.
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
        return {"error": f"Routes API {resp.status_code}: {resp.text[:300]}"}

    routes = resp.json().get("routes", [])
    if not routes:
        return {"error": "No route found"}
    route = routes[0]

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
        "total_duration_min": round(total_duration_s / 60),
        "legs": [
            {
                "distance_m": leg.get("distanceMeters", 0),
                "duration_min": round(_seconds(leg.get("duration", "0s")) / 60),
            }
            for leg in route.get("legs", [])
        ],
        "map_url": map_url,
    }
