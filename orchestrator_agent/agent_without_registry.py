"""OrchestratorAgent WITHOUT Agent Registry — the "before" state.

Structurally mirrors agent.py: a SequentialAgent with three sub-agents.
The middle step is the only one that differs — instead of a Registry search,
it consults a hardcoded routing table baked into the prompt.

  agent.py (with Registry)         agent_without_registry.py (this file)
  ────────────────────────         ──────────────────────────────────────
  1. topic_extractor               1. topic_extractor               (same)
  2. registry_finder               2. keyword_router                (hardcoded!)
        ↳ tool: registry_search_agents     ↳ no tool — table in prompt
  3. a2a_dispatcher                3. a2a_dispatcher
        ↳ tool: call_remote_a2a_agent      ↳ tool: call_a2a_agent (key-based)

What still hurts:
  - New agent type? Update KNOWN_AGENTS and the keyword_router prompt + redeploy.
  - Move an agent? Update KNOWN_AGENTS + redeploy.
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

from google.adk.agents import SequentialAgent
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


def _model() -> Gemini:
    # Gemini 3 Flash preview — needs strong instruction following to stick to
    # the strict pass-through routing without inventing extra steps.
    return Gemini(model="gemini-3-flash-preview")


# ---------------------------------------------------------------------------
# Step 1 — extract the single primary topic (identical to agent.py)
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
# Step 2 — keyword router (the Registry's hardcoded shadow)
# In agent.py this step calls registry_search_agents. Here, the routing table
# lives IN the prompt — every change requires editing this file.
# ---------------------------------------------------------------------------
ROUTER_INSTRUCTION = """You pick which A2A agent to call from a HARDCODED list.

Primary topic (from previous step): {primary_topic}

The ONLY agents that exist in this orchestrator are:

  - trip_planner: plans short city trips (Kyoto, Lisbon, San Francisco, etc.)
                  Match keywords: trip, travel, vacation, itinerary, or any
                  city name (Kyoto / Lisbon / Tokyo / Paris / …).

  - dog_walker:   plans dog walks and multi-day pet care.
                  Match keywords: dog, walk, pet, Buddy.

PROCESS — exactly these steps:
1. Compare the primary topic against the two entries above.
2. If the topic clearly matches ONE of them, output ONLY that key
   (`trip_planner` or `dog_walker`) on one line — no preamble, no quotes.
3. If the topic does NOT match either (e.g. flights, email, code review),
   output the single word `none` on one line.

FORBIDDEN:
- Inventing keys not in the list.
- Outputting anything other than `trip_planner`, `dog_walker`, or `none`.
- Adding commentary.
"""

keyword_router = LlmAgent(
    model=_model(),
    name="keyword_router",
    instruction=ROUTER_INSTRUCTION,
    output_key="agent_key",
)


# ---------------------------------------------------------------------------
# Step 3 — dispatch via A2A (mirrors agent.py's a2a_dispatcher, but the tool
# takes a key-from-table instead of a Registry resource name).
# ---------------------------------------------------------------------------
DISPATCHER_INSTRUCTION = """You dispatch the user's ORIGINAL message to a remote A2A agent.

Chosen agent key (from previous step): {agent_key}

Tool:
- `call_a2a_agent` — POST a message to one of the hardcoded agents.

PROCESS — exactly these steps:

A. If `{agent_key}` is `none`:
   Do NOT call any tool. Return EXACTLY this text as your final answer:

     "I don't have an agent registered for that. With Agent Registry, I could
      have searched by capability — but in this version I only know about
      trip_planner and dog_walker."

B. Otherwise, call `call_a2a_agent` ONCE with:
     agent_key = {agent_key}
     message   = the USER'S ORIGINAL MESSAGE from the start of this
                 conversation, copied CHARACTER-FOR-CHARACTER — every comma,
                 name, side request, and afterthought included. Do NOT use
                 the topic; use the full original user message.
   Then return the remote agent's `response` field as your final answer,
   VERBATIM. Do NOT prepend, append, or comment.

FORBIDDEN:
- Sending only the topic instead of the original message.
- Adding commentary about what the remote agent did or didn't do.
- Calling the tool when agent_key is `none`.
"""

a2a_dispatcher = LlmAgent(
    model=_model(),
    name="a2a_dispatcher",
    instruction=DISPATCHER_INSTRUCTION,
    tools=[call_a2a_agent],
)


# ---------------------------------------------------------------------------
# Root workflow — same shape as agent.py's SequentialAgent.
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="orchestrator_no_registry",
    sub_agents=[topic_extractor, keyword_router, a2a_dispatcher],
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
