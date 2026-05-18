# Demo Guide — how to actually show this off

This guide answers: *"I have 4 working agents. How do I demo them in a way that makes each concept (ADK, A2A, Agent Registry, MCP, skills) visible to my audience?"*

---

## The 4 visibility tools (use the right one for each concept)

| Tool | What it shows | When to use it |
|---|---|---|
| **`adk web`** | Per-agent chat UI with tool-call trace, event timeline | Demoing the **ADK agent** itself — its reasoning loop and tool calls |
| **A2A Inspector** ([github](https://github.com/a2aproject/a2a-inspector), [online](https://a2ainspect.com/)) | Agent card, send A2A messages, see JSON-RPC traffic | Demoing **A2A protocol** — proves the agent speaks A2A, not just ADK internals |
| **GCP Console → Agent Registry** ([console.cloud.google.com](https://console.cloud.google.com/agent-platform/agent-registry?project=neon-emitter-458622-e3)) | Registered agents, indexed skills, search UI | Demoing **Agent Registry** — the "yellow pages" view |
| **`curl` + the orchestrator's trace** | Raw agent card, live tool calls | Demoing **MCP** (registry MCP toolset) and **skills** (search results) |

---

## The story arc (5–10 min live demo)

The structure: **build up to peer-to-peer**. Each step adds one concept.

### Setup (before the audience walks in)

```bash
cd /Users/annie/Documents/Demo/agent_marketplace_demo
./deploy/start_local.sh
```

This starts DogWalker (:8001), TripPlanner (:8002), and registers both in your `neon-emitter-458622-e3` Registry. Open these tabs:

1. **GCP Console Agent Registry**: https://console.cloud.google.com/agent-platform/agent-registry?project=neon-emitter-458622-e3
2. **A2A Inspector** (online): https://a2ainspect.com/
3. **Terminal** with the project directory

---

### Act 1 — *"What's an ADK agent?"* (90 sec)

**Say:** *"ADK is Google's open-source Agent Development Kit. An ADK agent is an LLM plus tools. Here's one."*

**Show:** [dog_walker_agent/agent.py](./dog_walker_agent/agent.py) — the `LlmAgent(model=Gemini, instruction=..., tools=[get_dog_profile, get_weather, find_dog_parks, get_walking_route])`. ~10 lines of actual agent definition.

**Run live in another terminal:**

```bash
uv run adk web .
```

Browse to http://localhost:8000, pick `dog_walker_agent` from the dropdown, type:

> *Walk Buddy this afternoon, we live at 24th and Mission SF*

**Audience sees:** the tool calls happening live in the UI — `get_dog_profile → get_weather → find_dog_parks → get_walking_route`, then a final plan with a real SF map URL.

**Punchline:** *"That's an ADK agent. LLM + tools + reasoning. Nothing fancy yet."*

---

### Act 2 — *"What's an Agent Card? What's A2A?"* (90 sec)

**Say:** *"Now I want this agent to be callable over the network, not just from my laptop. That's what A2A is for."*

**Show the agent card** (raw, in terminal):

```bash
curl -s http://localhost:8001/.well-known/agent-card.json | jq .
```

Audience sees the JSON: name, description, **skills array with 3 entries** (`plan_walk`, `recommend_dog_park`, `check_walk_conditions`), each with `description` and `tags`.

**Say:** *"The agent card is A2A's contract — anyone who fetches it knows what this agent can do. The skills array is the discovery primitive."*

**Switch to A2A Inspector** at https://a2ainspect.com/. Enter `http://localhost:8001` as the agent URL.

> ⚠ A2A Inspector runs in the browser and connects directly to your localhost URL — needs to be on the same machine. If you're presenting on Zoom, run the [local Docker version](https://github.com/a2aproject/a2a-inspector#getting-started) instead.

The Inspector shows:
- **Agent Card tab**: the same JSON you just curled, but rendered nicely
- **Chat tab**: send a message, see the response
- **Console tab**: raw JSON-RPC traffic ("here are the bytes on the wire")

Send: *"Walk Buddy this afternoon at 24th and Mission SF"*

Audience sees the A2A protocol talking — message goes out, response comes back, all wrapped in JSON-RPC 2.0.

**Punchline:** *"This is A2A. Same agent, but now it speaks a standard wire protocol. Anyone on the network can call it without knowing it's an ADK agent. Tomorrow we could replace this with a LangGraph agent and the protocol stays the same."*

---

### Act 3 — *"What's the Agent Registry? What about MCP?"* (2 min)

**Say:** *"OK, but how does anyone find this agent? Hardcoded URLs don't scale. That's what the Agent Registry is for."*

**Open GCP Console Agent Registry tab.** Audience sees a table:
- `dog_walker_agent` with 3 skills
- `trip_planner_agent` with 3 skills
- (whatever else exists in the project)

Click into `dog_walker_agent`. Show:
- Protocol: A2A_AGENT
- Interface URL: `http://localhost:8001/`
- Skills (with their descriptions + tags)

**Say:** *"The Registry scraped the agent card automatically when I deployed. The 3 skills are now searchable. Any other agent in my org can find this by capability — 'who can plan a dog walk?' — without hardcoding the URL."*

**Now bring in MCP.** Run in terminal:

```bash
uv run python -c "
import asyncio
from common.auth import get_dynamic_headers
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

async def main():
    ts = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url='https://agentregistry.googleapis.com/mcp',
            headers=get_dynamic_headers(),
        ),
        header_provider=get_dynamic_headers,
    )
    for t in await ts.get_tools():
        print(f'  - {t.name}')

asyncio.run(main())
"
```

Audience sees ~20 tools: `list_agents`, `search_agents`, `get_agent`, `list_mcp_servers`, `create_service`, etc.

**Say:** *"The Agent Registry is itself an MCP server. MCP is the protocol for tool calls. So my agents can use these registry tools to discover other agents. MCP and A2A coexist — MCP is for tools, A2A is for agents, and the Registry holds both."*

---

### Act 4 — *"Now watch them collaborate"* (2 min — the climax)

**Say:** *"Last act. I'm going to ask the Orchestrator to plan a Kyoto trip AND figure out what to do about my dog. Watch what happens."*

**Run:**

```bash
uv run python orchestrator_agent/agent.py "Going to Kyoto for 5 days next week, I love temples. What about Buddy while I am away?"
```

While it runs (~2 min), **narrate** the trace as it appears:

> *"Orchestrator just searched the Registry for 'trip' — found TripPlanner."*
>
> *"Sent a verbatim A2A message to TripPlanner at localhost:8002."*
>
> *"TripPlanner is calling Google Maps to find Kyoto attractions..."*
>
> *"Now TripPlanner sees 'Buddy' in the message. It's searching the Registry for 'dog'..."*
>
> *"...found DogWalker, calling it over A2A..."*
>
> *"DogWalker is planning a daily routine for Buddy."*
>
> *"Response coming back: full 5-day Kyoto itinerary + Buddy's daily walks."*

**Punchline:** *"Three agents, three discoveries, all via the Registry. None of them had any of the others' URLs in their code. If I added a third specialist tomorrow — a flight-booking agent — the orchestrator would route to it the moment I registered it. That's the point of capability-based discovery."*

---

## Concept-by-concept cheat sheet

When a teammate asks "what is X?", here's what to point at:

### ADK (Agent Development Kit)
- **What:** Google's open-source SDK for building agents. Cross-language (Python, Go, Java, TS).
- **Where in demo:** [dog_walker_agent/agent.py](./dog_walker_agent/agent.py) — the `LlmAgent(...)` call.
- **Visibility:** `adk web` shows tool calls + traces interactively.

### A2A (Agent-to-Agent protocol)
- **What:** Open wire protocol for agents to talk to other agents (JSON-RPC over HTTP). Lets agents from different frameworks/vendors interop.
- **Where in demo:** [dog_walker_agent/server.py](./dog_walker_agent/server.py) wraps the agent with `to_a2a()`. The orchestrator's `call_remote_a2a_agent` sends messages.
- **Visibility:** A2A Inspector shows the wire protocol. The `/.well-known/agent-card.json` is the entry point.

### Agent Card
- **What:** A JSON document the agent serves at `/.well-known/agent-card.json` describing its name, URL, version, and **skills**. The discovery contract.
- **Where in demo:** [dog_walker_agent/agent_card.py](./dog_walker_agent/agent_card.py) — built with `AgentCard(...)`, served by `to_a2a()`.
- **Visibility:** `curl http://localhost:8001/.well-known/agent-card.json | jq .` or A2A Inspector's Agent Card tab.

### Skills
- **What:** Structured capability declarations in an agent card. Each has an `id`, `name`, `description`, `tags`, `examples`. **Indexed by the Registry for search.**
- **Where in demo:** `skills=[...]` in [agent_card.py](./dog_walker_agent/agent_card.py). Three per agent.
- **Visibility:** Visible in the agent card JSON, in the GCP Console Agent Registry detail page, and queryable via `registry_search_agents`.

### Agent Registry
- **What:** A Google Cloud catalog (yellow pages) of all agents and MCP servers in your project. Stores metadata; agents scrape it for discovery.
- **Where in demo:** Both A2A agents are registered (see [register.py](./dog_walker_agent/register.py)). Orchestrator + TripPlanner search it.
- **Visibility:** Three views:
  1. GCP Console → Agent Registry → Agents tab
  2. `gcloud alpha agent-registry agents list`
  3. Programmatic via `AgentRegistry` Python client or the Registry MCP server

### MCP (Model Context Protocol)
- **What:** Open protocol for an agent to call **tools** (functions / data sources). Complements A2A — MCP is "tool calls," A2A is "agent calls."
- **Where in demo:** Two places:
  - The **Registry itself** is an MCP server — `https://agentregistry.googleapis.com/mcp` — exposing `search_agents`, `list_agents`, etc.
  - The original [discovery_agent/](./discovery_agent/) (untouched from the upstream demo) shows generic MCP discovery
- **Visibility:** In the orchestrator's tool trace, the `registry_search_agents` calls are MCP tool calls. The Python snippet in Act 3 lists all 20+ Registry MCP tools.

---

## Suggested live demo cheat-sheet (one-pager)

```
0. Pre-show:
   ./deploy/start_local.sh
   Open tabs: GCP Console Agent Registry | A2A Inspector | Terminal

1. ADK agent (90s):
   Show agent.py
   uv run adk web .
   → "Walk Buddy this afternoon at 24th and Mission SF"
   Audience sees: tool calls live, then a real plan

2. Agent Card + A2A (90s):
   curl -s http://localhost:8001/.well-known/agent-card.json | jq .
   Open A2A Inspector → http://localhost:8001
   Send same prompt
   Audience sees: agent card, JSON-RPC wire traffic

3. Agent Registry + MCP (2min):
   Open GCP Console → Agent Registry → Agents tab
   Click dog_walker_agent → show skills, URL, protocol
   Run the "list MCP tools" snippet in terminal
   Audience sees: yellow pages view + the Registry's own MCP API

4. Peer-to-peer (2min — climax):
   uv run python orchestrator_agent/agent.py "Going to Kyoto for 5 days next week, I love temples. What about Buddy while I am away?"
   Narrate the trace as it runs (~2 min execution)
   Audience sees: 3 discoveries, 2 A2A delegations, real itinerary + dog plan

5. Q&A & cleanup:
   ./deploy/stop_local.sh --deregister
```

---

## Common questions you'll get

> **"Why not just put TripPlanner and DogWalker in the orchestrator as sub-agents?"**
> Because then they're tightly coupled — same process, same deploy, same team. A2A lets different teams own different agents, deploy them independently, and have them found by capability. It's the difference between functions and microservices.

> **"What's the difference between MCP and A2A really?"**
> MCP = the agent calls a *tool* (stateless function). A2A = the agent talks to *another agent* (stateful, reasons, may call its own tools/peers). MCP is "get_weather(SF)"; A2A is "ask my colleague the trip planner."

> **"How does deploying work?"**
> Locally we registered manually via `register.py`. In production, deploy each agent to **Vertex AI Agent Engine** and the Registry auto-discovers and indexes the agent card. Same orchestrator code, no changes. See [`deploy/agent_engine.md`](./deploy/agent_engine.md).

> **"Why register `localhost` URLs?"**
> So the educational demo works without paying for production deploys. **The Registry is a catalog, not a runtime** — it stores whatever URL you give it. `gcloud agent-registry services create` accepts any URL (localhost, Cloud Run, on-prem, a tunnel — anything). It doesn't host the agent; it just stores a pointer to where the agent lives. When you do deploy to Vertex AI Agent Engine, the Registry entry is created automatically with a real public URL, but the discovery code is identical.

> **"Wait, the Registry can show entries even when I haven't deployed?"**
> Yes — see above. Auto-registration on deploy is *one way* into the Registry. Manual `gcloud agent-registry services create` is *another way* with no deploy. The Registry doesn't know or care which path was used.

> **"Can other A2A frameworks (LangGraph, CrewAI) talk to your ADK agents?"**
> Yes — that's the whole point of A2A. We didn't demo cross-framework here, but the protocol is open and Microsoft/AWS/Salesforce/etc. all ship A2A-compatible runtimes.

---

## Troubleshooting during the demo

- **`adk web` won't show my agents:** make sure each agent folder has `__init__.py` exporting `root_agent` (they do, but worth re-checking after any edit).
- **A2A Inspector can't connect:** check ports — `lsof -ti:8001` and `lsof -ti:8002` should show pids. If empty, `./deploy/start_local.sh` again.
- **Orchestrator can't find an agent:** check the Registry — `gcloud alpha agent-registry agents list --location=global --project=neon-emitter-458622-e3`. If empty, rerun `register.py`.
- **API quota errors:** Maps APIs are billable. If you exceed free tier mid-demo, the agent will return errors — have a screenshot of a successful previous run as backup.
- **Demo takes >2 min:** the orchestrator → TripPlanner → DogWalker chain involves ~6 LLM calls and ~10 Maps calls. That's the cost of doing real work. If you need speed, pre-record a screen capture of one full run.
