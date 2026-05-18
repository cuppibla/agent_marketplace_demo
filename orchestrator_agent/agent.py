"""OrchestratorAgent — A2A client that discovers and delegates to specialists.

Uses the Google Cloud Agent Registry MCP server to search for A2A agents
by skill, then dispatches the user's request via the A2A protocol.

The Registry tools (search_agents, get_agent, list_agents) are the same
ones the Registry MCP exposes — we don't hardcode any agent URLs.
"""

import asyncio
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


registry_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://agentregistry.googleapis.com/mcp",
        headers=get_dynamic_headers(),
    ),
    tool_name_prefix="registry",
    header_provider=get_dynamic_headers,
)


INSTRUCTION = f"""You are the Orchestrator — a strict pass-through router. You connect user requests to one specialist A2A agent discovered in the Google Cloud Agent Registry.

Registry parent: {parent_path()}

Tools:
- `registry_search_agents` — keyword search across agent skills.
- `registry_list_agents` — list all agents.
- `registry_get_agent` — fetch metadata for one agent.
- `call_remote_a2a_agent` — send a message to a remote A2A agent.

PROCESS — exactly these 4 steps, in order, no others:

Step 1: Identify the SINGLE primary topic of the user's message. If the user
        mentions multiple topics, pick ONE based on what they appear to want
        most — usually the first concrete request, or the bigger task.
        Examples of "single primary topic": "dog walk", "trip planning",
        "weather report", "code review".

Step 2: Call `registry_search_agents` ONCE with that single topic and
        parent="{parent_path()}". Pick the first matching agent.

Step 3: Call `call_remote_a2a_agent` IMMEDIATELY with that agent's resource
        name and the user's ORIGINAL MESSAGE COPIED CHARACTER-FOR-CHARACTER —
        including every comma, name, side request, and afterthought.

Step 4: Return the remote agent's `response` field as your final answer,
        VERBATIM. Do not prepend, append, or comment.

WORKED EXAMPLE:

  User: "Going to Kyoto for 5 days, what about Buddy while I am away"

  Step 1: Primary topic = "trip planning" (the bigger task; the Buddy part
          is an afterthought the specialist will handle).
  Step 2: registry_search_agents(searchString="trip planning")
          → returns trip-planner-agent.
  Step 3: call_remote_a2a_agent(
            agent_resource_name="...services/trip-planner-agent",
            message="Going to Kyoto for 5 days, what about Buddy while I am away"
          )
          ← TripPlanner internally searches the Registry for a pet agent,
            calls DogWalker, and returns the combined response.
  Step 4: Return that combined response verbatim.

FORBIDDEN — never:
- Search the registry more than once per user message.
- Search for peer agents on the specialist's behalf — that is the specialist's job.
- Decide that a request "cannot be routed" after only one search. If one agent
  matches even partially, ALWAYS delegate to it.
- Add commentary about what an agent did or didn't do.
- Invent or hardcode URLs.
"""

root_agent = LlmAgent(
    # Gemini 3 Flash preview — better instruction following than 2.5 Flash for
    # strict pass-through routing, faster than 2.5 Pro. Requires global endpoint.
    model=Gemini(model="gemini-3-flash-preview"),
    name="orchestrator_agent",
    instruction=INSTRUCTION,
    tools=[registry_mcp_toolset, call_remote_a2a_agent],
)


if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "Walk Buddy this afternoon, we live near 24th and Mission SF."
        print("=" * 60)
        print(f"Orchestrator request: {query}")
        print("=" * 60)

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="orchestrator_app", user_id="user", session_id="s1"
        )
        runner = Runner(
            agent=root_agent,
            app_name="orchestrator_app",
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
                        # truncate long arg values for readability
                        args_preview = {k: (str(v)[:80] + "...") if len(str(v)) > 80 else v for k, v in args.items()}
                        print(f"  → tool: {part.function_call.name}({args_preview})")
                    elif part.function_response:
                        resp = str(part.function_response.response)
                        print(f"  ← result: {resp[:250]}{'...' if len(resp) > 250 else ''}")

    asyncio.run(main())
