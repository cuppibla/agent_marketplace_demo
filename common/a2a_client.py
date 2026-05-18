"""Shared helper to call any A2A agent registered in the Agent Registry.

Used by OrchestratorAgent (to delegate to specialists) and by specialists
that want to delegate to peers (e.g. TripPlanner asking DogWalker about pet
care during a trip).
"""

import uuid

import httpx

from a2a.client import ClientConfig, ClientFactory
from a2a.types import AgentCard, Message, Part, Role, TextPart

from common.registry_client import get_registry


async def call_remote_a2a_agent(agent_resource_name: str, message: str) -> dict:
    """Send a message to an A2A agent registered in the Agent Registry.

    Args:
        agent_resource_name: Full resource name from the Registry
            (e.g. projects/.../locations/.../agents/agentregistry-...).
        message: The natural-language task to send to the remote agent.

    Returns:
        The agent's text response plus the URL it was reached at.
    """
    registry = get_registry()
    info = registry.get_agent_info(agent_resource_name)
    interfaces = info.get("protocols", [{}])[0].get("interfaces", [])
    if not interfaces:
        return {"error": f"Agent has no A2A interface: {agent_resource_name}"}
    url = interfaces[0]["url"].rstrip("/")
    card_url = f"{url}/.well-known/agent-card.json"

    async with httpx.AsyncClient(timeout=180.0) as http:
        resp = await http.get(card_url)
        if resp.status_code != 200:
            return {"error": f"Could not fetch agent card at {card_url} ({resp.status_code})"}
        card = AgentCard.model_validate(resp.json())

        factory = ClientFactory(config=ClientConfig(httpx_client=http, streaming=False))
        client = factory.create(card)
        msg = Message(
            kind="message",
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(kind="text", text=message))],
        )

        response_text_parts: list[str] = []
        async for event in client.send_message(msg):
            if isinstance(event, tuple):
                for e in event:
                    if e is None or not hasattr(e, "history") or not e.history:
                        continue
                    for m in e.history:
                        if getattr(m, "role", None) != Role.agent or not m.parts:
                            continue
                        for p in m.parts:
                            if hasattr(p.root, "text") and p.root.text:
                                response_text_parts.append(p.root.text)

        if not response_text_parts:
            return {"error": "Agent returned no text response", "url": url}
        return {"response": "\n".join(response_text_parts), "agent_url": url}
