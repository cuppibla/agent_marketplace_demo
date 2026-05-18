"""Register the locally-running TripPlannerAgent in the Agent Registry."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SERVICE_ID = "trip-planner-agent"
PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("AGENT_REGISTRY_LOCATION", "global")
HOST = os.environ.get("TRIP_PLANNER_HOST", "localhost")
PORT = int(os.environ.get("TRIP_PLANNER_PORT", "8002"))


def fetch_local_card() -> dict:
    url = f"http://{HOST}:{PORT}/.well-known/agent-card.json"
    print(f"Fetching agent card from {url}")
    resp = httpx.get(url, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def delete_existing() -> None:
    name = f"projects/{PROJECT}/locations/{LOCATION}/services/{SERVICE_ID}"
    print(f"Removing any existing service: {name}")
    subprocess.run(
        ["gcloud", "alpha", "agent-registry", "services", "delete", name, "--quiet"],
        capture_output=True, text=True,
    )


def create_service(card: dict) -> None:
    print(f"Creating service '{SERVICE_ID}' in {PROJECT}/{LOCATION}")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(card, tmp)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [
                "gcloud", "alpha", "agent-registry", "services", "create",
                SERVICE_ID,
                f"--location={LOCATION}",
                f"--project={PROJECT}",
                f"--display-name={card.get('name', 'TripPlannerAgent')}",
                f"--description={card.get('description', '')[:200]}",
                "--agent-spec-type=a2a-agent-card",
                f"--agent-spec-content={tmp_path}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            sys.exit(result.returncode)
        print(result.stdout)
    finally:
        os.unlink(tmp_path)

    name = f"projects/{PROJECT}/locations/{LOCATION}/services/{SERVICE_ID}"
    print(f"\n✓ Registered. Resource name:\n  {name}")


if __name__ == "__main__":
    card = fetch_local_card()
    delete_existing()
    create_service(card)
