"""TripPlannerAgent (no-registry variant) — same behaviour as `agent.py`,
but the peer hand-off to DogWalker uses a HARDCODED URL instead of dynamic
Agent Registry discovery.

This file exists to make the "before vs. after" contrast obvious:

  agent.py                  agent_no_registry.py
  --------                  --------------------
  Registry MCP toolset      ✗  removed
  registry_search_agents    ✗  removed
  Peer discovered at        ✗  Peer hardcoded as
    runtime by skill           DOG_WALKER_URL constant
  Adding a new peer:        Adding a new peer:
    deploy + register          edit this file, add a new
    once, every other          tool function and another
    agent finds it             constant — for EVERY caller

Everything else (tools, planning prompt, peer-delegation flow) is identical.
"""

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

from trip_planner_agent.tools import (
    find_attractions,
    get_walking_route,
    get_weather,
)


# ---------------------------------------------------------------------------
# Hardcoded peer wiring — the part the Registry would normally hide.
# Each known peer needs its own URL constant AND its own tool function below.
# Compare with agent.py, which discovers any peer via registry_search_agents.
# ---------------------------------------------------------------------------
DOG_WALKER_URL = os.environ.get("DOG_WALKER_URL", "http://localhost:8001")


async def _call_a2a_by_url(url: str, message: str) -> dict:
    """Plain A2A call that fetches the agent card and posts a message.

    This is what `common.a2a_client.call_remote_a2a_agent` does AFTER it
    resolves a Registry resource name → URL. Without the Registry we have to
    know the URL up front.
    """
    url = url.rstrip("/")
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


async def call_dog_walker(message: str) -> dict:
    """Send a pet-care request to the DogWalker agent.

    Args:
        message: Natural-language request, e.g. "Plan care for Buddy while
                 we are away in Kyoto for 5 days."

    Returns:
        {"response": "...", "agent_url": "..."} or {"error": "..."}.

    Note: in the registry-enabled version the agent would find DogWalker
    dynamically by searching for "dog". Here, this tool is wired by hand —
    if DogWalker moves or is replaced, this file must change.
    """
    return await _call_a2a_by_url(DOG_WALKER_URL, message)


INSTRUCTION = f"""You are TripPlannerAgent — a thoughtful trip planner for short city trips.

When a user asks you to plan a trip:

1. Call `get_weather` for the destination to know what to expect.
2. Call `find_attractions` (with category="tourist attractions") to get top sights.
3. Call `find_attractions` again with category="restaurants" or "cafes" if relevant.
4. REASON about a sensible day-by-day itinerary:
   - Group attractions geographically (don't crisscross the city)
   - Mix high-energy and low-energy activities
   - Leave time for meals
   - Adapt to weather (indoor on rainy days)
5. Use `get_walking_route` between stops to check distances.
6. Return a clear itinerary with: trip summary, day-by-day plan, weather notes,
   and a map URL for at least the first day.

PEER DELEGATION — if the user mentions a pet or dog by name (e.g. "Buddy"):
After producing the itinerary, you MUST hand off to the DogWalker peer.
Use these exact steps:
  a. Call `call_dog_walker` with a concrete request, e.g.:
       "Plan care for Buddy while we are away in Kyoto for 5 days starting next week."
  b. Append the peer's full `response` field under a
       "**Pet care for [pet name]**"
     section at the end of your output.

(In this configuration the DogWalker URL is hardcoded — {DOG_WALKER_URL}.
Adding a second peer would require a new tool function in this file. The
registry-enabled variant in agent.py avoids both.)

WORKED EXAMPLE — user message: "Going to Kyoto for 5 days, what about Buddy"
  1. Build the Kyoto itinerary using your own tools.
  2. call_dog_walker(message="Plan care for Buddy while we are away in Kyoto for 5 days.")
  3. Append the response under "Pet care for Buddy".

Be specific. Mention real place names from `find_attractions`. Don't invent attractions.
"""

root_agent = LlmAgent(
    # Gemini 3 Flash preview — needs strong instruction-following for the
    # peer-delegation step (must call call_dog_walker, not give up).
    model=Gemini(model="gemini-3-flash-preview"),
    name="trip_planner_agent_no_registry",
    instruction=INSTRUCTION,
    tools=[
        get_weather,
        find_attractions,
        get_walking_route,
        call_dog_walker,
    ],
)


if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "Plan a 2-day trip to Kyoto, Japan. I love temples and street food, and what about Buddy?"
        print("=" * 60)
        print(f"TripPlanner (no-registry) request: {query}")
        print(f"DogWalker URL: {DOG_WALKER_URL}")
        print("=" * 60)

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="trip_planner_no_registry_app", user_id="user", session_id="s1"
        )
        runner = Runner(
            agent=root_agent,
            app_name="trip_planner_no_registry_app",
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
                print("ITINERARY:")
                print("=" * 60)
                print(event.content.parts[0].text)
                print("=" * 60)
            elif event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        print(f"  → tool: {part.function_call.name}({dict(part.function_call.args)})")
                    elif part.function_response:
                        resp = str(part.function_response.response)
                        print(f"  ← result: {resp[:200]}{'...' if len(resp) > 200 else ''}")

    asyncio.run(main())
