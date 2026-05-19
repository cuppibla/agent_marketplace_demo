"""OrchestratorAgent — A2A client that discovers and delegates to specialists.

Refactored as a SequentialAgent workflow with three sub-agents:
  1. topic_extractor  — picks the single primary topic from the user message
  2. registry_finder  — searches the Agent Registry for a matching A2A agent
  3. a2a_dispatcher   — sends the original user message to that agent and
                        returns the response verbatim

State flow (via output_key, surfaced into later instructions as {state_key}):
  primary_topic        → consumed by registry_finder
  agent_resource_name  → consumed by a2a_dispatcher
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google.adk.agents import SequentialAgent
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


# Gemini 3 Flash preview — better instruction following than 2.5 Flash for
# strict pass-through routing, faster than 2.5 Pro. Requires global endpoint.
def _model() -> Gemini:
    return Gemini(model="gemini-3-flash-preview")


# ---------------------------------------------------------------------------
# Step 1 — extract the single primary topic
# ---------------------------------------------------------------------------
TOPIC_INSTRUCTION = """You extract the SINGLE primary topic from the user's message.

Rules:
- Output ONLY the topic phrase on one line — no preamble, no punctuation, no quotes.
- If the user mentions multiple topics, pick ONE: usually the first concrete request,
  or the bigger task. Side requests and afterthoughts are NOT the primary topic.
- Valid examples: "dog walk", "trip planning", "weather report", "code review".

Worked example:
  User: "Going to Kyoto for 5 days, what about Buddy while I am away"
  → trip planning   (the Kyoto trip is the bigger task; Buddy is an afterthought)
"""

topic_extractor = LlmAgent(
    model=_model(),
    name="topic_extractor",
    instruction=TOPIC_INSTRUCTION,
    output_key="primary_topic",
)


# ---------------------------------------------------------------------------
# Step 2 — find the matching A2A agent in the Registry
# ---------------------------------------------------------------------------
FINDER_INSTRUCTION = f"""You find the right A2A agent in the Google Cloud Agent Registry.

Registry parent: {parent_path()}
Primary topic (from previous step): {{primary_topic}}

Tool:
- `registry_search_agents` — keyword search across agent skills.

PROCESS — exactly these steps:
1. Call `registry_search_agents` ONCE with:
     searchString="{{primary_topic}}"
     parent="{parent_path()}"
2. Pick the FIRST matching agent in the result.
3. Output ONLY that agent's resource name (the `name` field from its metadata),
   on one line, with no preamble, no commentary, no quotes.

FORBIDDEN:
- Searching more than once.
- Deciding "no match" — if any agent matches even partially, ALWAYS pick the first one.
- Adding any commentary.
- Inventing URLs or names.
"""

registry_finder = LlmAgent(
    model=_model(),
    name="registry_finder",
    instruction=FINDER_INSTRUCTION,
    tools=[registry_mcp_toolset],
    output_key="agent_resource_name",
)


# ---------------------------------------------------------------------------
# Step 3 — dispatch the user's ORIGINAL message via A2A
# ---------------------------------------------------------------------------
DISPATCHER_INSTRUCTION = """You dispatch the user's ORIGINAL message to a remote A2A agent.

Chosen agent (from previous step): {agent_resource_name}

Tool:
- `call_remote_a2a_agent` — send a message to a remote A2A agent.

PROCESS — exactly these steps:
1. Call `call_remote_a2a_agent` ONCE with:
     agent_resource_name = {agent_resource_name}
     message             = the USER'S ORIGINAL MESSAGE from the start of this
                           conversation, copied CHARACTER-FOR-CHARACTER —
                           every comma, name, side request, and afterthought
                           included. Do NOT use the topic; use the full original
                           user message.
2. Return the remote agent's `response` field as your final answer, VERBATIM.
   Do NOT prepend, append, or comment.

FORBIDDEN:
- Sending only the topic instead of the original message.
- Adding commentary about what the remote agent did or didn't do.
- Inventing or hardcoding URLs.
"""

a2a_dispatcher = LlmAgent(
    model=_model(),
    name="a2a_dispatcher",
    instruction=DISPATCHER_INSTRUCTION,
    tools=[call_remote_a2a_agent],
)


# ---------------------------------------------------------------------------
# Root workflow — runs the three steps in order
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="orchestrator_agent",
    sub_agents=[topic_extractor, registry_finder, a2a_dispatcher],
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

        final_text = None
        async for event in runner.run_async(
            user_id="user",
            session_id="s1",
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            ),
        ):
            author = getattr(event, "author", None) or "?"
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text
            elif event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        args = dict(part.function_call.args)
                        args_preview = {k: (str(v)[:80] + "...") if len(str(v)) > 80 else v for k, v in args.items()}
                        print(f"  [{author}] → tool: {part.function_call.name}({args_preview})")
                    elif part.function_response:
                        resp = str(part.function_response.response)
                        print(f"  [{author}] ← result: {resp[:250]}{'...' if len(resp) > 250 else ''}")
                    elif getattr(part, "text", None):
                        text = part.text.strip()
                        if text:
                            print(f"  [{author}] ✎ {text[:200]}{'...' if len(text) > 200 else ''}")

        if final_text is not None:
            print("\n" + "=" * 60)
            print("FINAL RESPONSE:")
            print("=" * 60)
            print(final_text)
            print("=" * 60)

    asyncio.run(main())
