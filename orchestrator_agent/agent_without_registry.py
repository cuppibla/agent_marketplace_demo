"""OrchestratorAgent WITHOUT Agent Registry — the "before" state.

This is what the orchestrator would look like if A2A were all we had.
Compare to agent.py (the Registry-driven version) to feel the difference.

What's different:
  - Hardcoded URL table at the top
  - Hardcoded routing logic (keyword-based if/elif via LLM instructions)
  - No `registry_search_agents`, no `registry_get_agent`
  - Cannot discover new agents — only the ones in KNOWN_AGENTS

What breaks:
  - New agent type? Update this file + redeploy.
  - Move an agent? Update this file + redeploy.
  - Another team built a perfect agent? You don't know it exists.
  - Ask for something not in the dict? "I cannot help with that."

Run it:
  uv run python orchestrator_agent/agent_without_registry.py "Walk Buddy"
  uv run python orchestrator_agent/agent_without_registry.py "Book a flight to Tokyo"
  # ↑ this one fails — no agent for flights in KNOWN_AGENTS
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import AgentCard, Message, Part, Role, TextPart

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini


# ──────────────────────────────────────────────────────────────────────────────
# ❌ THE HARDCODED ROUTING TABLE — this is what the Registry would replace.
# Every new agent that ships in the company requires updating this dict and
# redeploying this orchestrator.
# ──────────────────────────────────────────────────────────────────────────────
KNOWN_AGENTS: dict[str, str] = {
    "trip_planner": "http://localhost:8002",
    "dog_walker":   "http://localhost:8001",
    # When the flight-booking team ships their agent, add:
    #   "flight_booker": "http://flights.internal/",
    # And redeploy.
    # When the support team's triage agent appears:
    #   "support_triage": "http://support.internal/",
    # And redeploy.
    # And every developer who wants to call from their orchestrator
    # maintains the same kind of dict in their own codebase.
}


async def call_a2a_agent(agent_key: str, message: str) -> dict:
    """Send a message to one of the known A2A agents.

    Args:
        agent_key: One of the keys in KNOWN_AGENTS (e.g. 'trip_planner').
                   If the agent_key is not known, returns an error — there is
                   no way to discover other agents without the Agent Registry.
        message:   The natural-language task to send, verbatim.

    Returns:
        The remote agent's text response and the URL it was reached at.
    """
    if agent_key not in KNOWN_AGENTS:
        return {
            "error": (
                f"Unknown agent '{agent_key}'. I only know: "
                f"{list(KNOWN_AGENTS.keys())}. "
                f"To add a new agent, someone has to update KNOWN_AGENTS in "
                f"orchestrator_agent/agent_without_registry.py and redeploy."
            )
        }

    url = KNOWN_AGENTS[agent_key].rstrip("/")
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


# ──────────────────────────────────────────────────────────────────────────────
# ❌ THE HARDCODED ROUTING LOGIC — also what the Registry would replace.
# The orchestrator has to know in advance which keywords map to which agent.
# A new agent type means updating this prompt as well.
# ──────────────────────────────────────────────────────────────────────────────
INSTRUCTION = """You are the Orchestrator (NO-REGISTRY VERSION).

You only know two agents — they're hardcoded in your code:

  - trip_planner: plans short city trips (Kyoto, Lisbon, San Francisco, etc.)
                  Use when the message mentions: trip, travel, vacation, itinerary,
                  or a city name like Kyoto / Lisbon / Tokyo / Paris.

  - dog_walker:   plans dog walks and multi-day pet care.
                  Use when the message mentions: dog, walk, pet, Buddy.

PROCESS — exactly 3 steps:

Step 1: Pick the matching agent_key from the two above by reading the user's
        message for keywords. If the user mentions BOTH topics (e.g. a trip AND
        their dog), pick the BIGGER task — the trip — and forward verbatim;
        the trip planner can handle the rest internally.

Step 2: Call `call_a2a_agent` with that agent_key and the user's ORIGINAL
        message copied character-for-character.

Step 3: Return the response verbatim. Do not add commentary.

IF THE USER ASKS FOR SOMETHING NOT IN YOUR LIST (e.g. "book a flight",
"summarize an email", "review code"), you have NO way to find an agent for it.
Say so honestly:

    "I don't have an agent registered for that. With Agent Registry, I could
     have searched by capability — but in this version I only know about
     trip_planner and dog_walker."

This is the cost of not using the Registry. Every new capability requires
updating my KNOWN_AGENTS dict and redeploying me.
"""

root_agent = LlmAgent(
    model=Gemini(model="gemini-3-flash-preview"),
    name="orchestrator_no_registry",
    instruction=INSTRUCTION,
    tools=[call_a2a_agent],
)


if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "Walk Buddy this afternoon at 24th and Mission SF."
        print("=" * 60)
        print(f"NO-REGISTRY Orchestrator request: {query}")
        print(f"KNOWN_AGENTS: {list(KNOWN_AGENTS.keys())}")
        print("=" * 60)

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="orchestrator_no_registry_app", user_id="user", session_id="s1"
        )
        runner = Runner(
            agent=root_agent,
            app_name="orchestrator_no_registry_app",
            session_service=session_service,
        )

        async for event in runner.run_async(
            user_id="user",
            session_id="s1",
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            ),
        ):
            if event.is_final_response():
                print("\n" + "=" * 60)
                print("FINAL RESPONSE:")
                print("=" * 60)
                print(event.content.parts[0].text)
                print("=" * 60)
            elif event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        args = dict(part.function_call.args)
                        args_preview = {k: (str(v)[:80] + "...") if len(str(v)) > 80 else v for k, v in args.items()}
                        print(f"  → tool: {part.function_call.name}({args_preview})")
                    elif part.function_response:
                        resp = str(part.function_response.response)
                        print(f"  ← result: {resp[:250]}{'...' if len(resp) > 250 else ''}")

    asyncio.run(main())
