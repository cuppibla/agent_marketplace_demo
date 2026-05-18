"""Thin wrapper around the Agent Registry client used by all agents."""

import os
from google.adk.integrations.agent_registry import AgentRegistry


def get_registry() -> AgentRegistry:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("AGENT_REGISTRY_LOCATION", "global")
    return AgentRegistry(project_id=project, location=location)


def parent_path() -> str:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("AGENT_REGISTRY_LOCATION", "global")
    return f"projects/{project}/locations/{location}"
