"""DogWalkerAgent — plans personalized dog walks using maps + weather + dog profile.

Phase 1: plain LlmAgent (no A2A yet). Phase 2 wraps this in to_a2a().
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini

from dog_walker_agent.tools import (
    find_dog_parks,
    get_dog_profile,
    get_walking_route,
    get_weather,
)

INSTRUCTION = """You are DogWalkerAgent — a thoughtful dog-walking planner.

DEFAULTS: home address = {home}, city for weather = {city}. Use these unless
the user gives different ones.

CASE A — Single walk ("walk Buddy this afternoon", "morning walk"):

1. Call `get_dog_profile` to learn the dog's breed, energy, and constraints.
2. Call `get_weather` for the user's city.
3. Call `find_dog_parks` near home.
4. Pick 1–2 parks given the dog's energy, weather, last_walked time, and walking distance.
5. Call `get_walking_route` (home → stops → home).
6. Return: one-line summary, route breakdown, any warnings, map URL.

CASE B — Extended absence ("while I'm away", "for the next 3 days", "while in Kyoto"):

Do NOT decline. The user wants a routine, not a one-off walk. Instead:
1. Call `get_dog_profile` and `get_weather`.
2. Call `find_dog_parks` to know what's nearby.
3. Propose a daily schedule, e.g.:
   - Morning walk (~8 AM, 25–30 min, neighborhood loop for a bathroom break)
   - Afternoon walk (~5 PM, 45–60 min, longer outing to a nearby park)
4. Pick one or two specific parks from the list and name them in the schedule.
5. Note that for multi-day absences, the user should also consider a pet sitter
   or boarding to provide companionship between walks, and remind them to leave
   food, water, and emergency contact info.
6. Return: a "Daily routine" section + "Logistics" section. No map URL needed
   for routines — the schedule is what matters.

Be specific and short. Mention real park names from `find_dog_parks`.
""".format(
    home=os.environ.get("DEMO_HOME_ADDRESS", "24th & Mission, San Francisco, CA"),
    city=os.environ.get("DEMO_CITY", "San Francisco"),
)

root_agent = LlmAgent(
    # Gemini 3 Flash preview — consistent with the other agents in this demo.
    model=Gemini(model="gemini-3-flash-preview"),
    name="dog_walker_agent",
    instruction=INSTRUCTION,
    tools=[get_dog_profile, get_weather, find_dog_parks, get_walking_route],
)


if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "Walk Buddy this afternoon."
        print("=" * 60)
        print(f"DogWalker request: {query}")
        print("=" * 60)

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="dog_walker_app", user_id="user", session_id="s1"
        )
        runner = Runner(
            agent=root_agent,
            app_name="dog_walker_app",
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
                print("PLAN:")
                print("=" * 60)
                print(event.content.parts[0].text)
                print("=" * 60)
            elif event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        print(f"  → tool: {part.function_call.name}({dict(part.function_call.args)})")
                    elif part.function_response:
                        # short preview only
                        resp = str(part.function_response.response)
                        print(f"  ← result: {resp[:200]}{'...' if len(resp) > 200 else ''}")

    asyncio.run(main())
