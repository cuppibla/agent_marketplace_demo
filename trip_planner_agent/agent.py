"""TripPlannerAgent — plans short trips using real maps + weather.

Phase 4: plain LlmAgent with planning tools. Wrapped as A2A in server.py.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from common.a2a_client import call_remote_a2a_agent
from common.auth import get_dynamic_headers
from common.registry_client import parent_path

from trip_planner_agent.tools import (
    find_attractions,
    get_walking_route,
    get_weather,
)

# Peer discovery: TripPlanner uses the same Registry MCP toolset as the
# orchestrator. This is what makes the demo's peer-to-peer story real —
# an A2A agent discovering another A2A agent through the Registry, with
# no hardcoded URLs.
registry_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://agentregistry.googleapis.com/mcp",
        headers=get_dynamic_headers(),
    ),
    tool_name_prefix="registry",
    header_provider=get_dynamic_headers,
)

INSTRUCTION = f"""You are TripPlannerAgent — a thoughtful trip planner for short city trips.

Registry parent: {parent_path()}

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
After producing the itinerary, you MUST find and call a pet-care peer agent.
Use these exact steps:
  a. Call `registry_search_agents` with parent="{parent_path()}" and
     searchString="dog" (one word, simple — match by tag, not phrase).
  b. From the results, pick any agent whose skills include walking or pet care.
     If there is at least one match, ALWAYS use it — do not give up.
  c. Call `call_remote_a2a_agent` with that agent's resource name and a
     concrete request like: "Plan care for Buddy while we are away in Kyoto
     for 5 days starting next week."
  d. Append the peer's full response under a "**Pet care for [pet name]**"
     section at the end of your output.

WORKED EXAMPLE — user message: "Going to Kyoto for 5 days, what about Buddy"
  1. Build the Kyoto itinerary using your own tools.
  2. registry_search_agents(searchString="dog") → finds dog-walker-agent.
  3. call_remote_a2a_agent(
       agent_resource_name="...services/dog-walker-agent",
       message="Plan care for Buddy while we are away in Kyoto for 5 days."
     )
  4. Append the response under "Pet care for Buddy".

Be specific. Mention real place names from `find_attractions`. Don't invent attractions.
"""

root_agent = LlmAgent(
    # Gemini 3 Flash preview — needs strong instruction-following for the
    # peer-discovery step (must search Registry and delegate, not give up).
    model=Gemini(model="gemini-3-flash-preview"),
    name="trip_planner_agent",
    instruction=INSTRUCTION,
    tools=[
        get_weather,
        find_attractions,
        get_walking_route,
        registry_mcp_toolset,
        call_remote_a2a_agent,
    ],
)


if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "Plan a 2-day trip to Kyoto, Japan. I love temples and street food."
        print("=" * 60)
        print(f"TripPlanner request: {query}")
        print("=" * 60)

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="trip_planner_app", user_id="user", session_id="s1"
        )
        runner = Runner(
            agent=root_agent,
            app_name="trip_planner_app",
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
