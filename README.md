# Agent Marketplace Demo

A runnable demo + 4-part developer tutorial showing **A2A + Agent Registry + MCP** working together on Google Cloud.

> Four agents collaborate to plan trips and walk a dog — all discoverable through the Google Cloud Agent Registry. No hardcoded agent URLs anywhere.

---

## How the Agent Registry actually works (read this first)

A common misconception: *"agents only appear in the Registry if I deploy to Vertex AI Agent Engine."* That's wrong.

**The Registry is a catalog (yellow pages), not a runtime (hosting service).** It stores metadata about agents and MCP servers — name, URL, skills — but doesn't host or run anything. Two ways to populate it:

| Method | Command | URL points to |
|---|---|---|
| **Manual** | `gcloud agent-registry services create ...` | Anything — `localhost`, Cloud Run, on-prem, a tunnel, whatever |
| **Auto** | Deploy to Vertex AI Agent Engine | The deploy's auto-generated production URL |

This demo uses the **manual** path: [`dog_walker_agent/register.py`](./dog_walker_agent/register.py) calls `gcloud agent-registry services create` with `http://localhost:8001/` as the URL. The Registry happily stores that. The Orchestrator (also running locally) looks up the entry, gets the `localhost` URL, and connects to it because they're on the same machine.

This is the "fake deploy" trick that makes the local demo realistic without paying for Agent Engine. When you actually deploy to Agent Engine, only **one thing changes**: the URL in the Registry becomes a real public URL. All the discovery code stays the same.

> See [CHANGELOG.md](./CHANGELOG.md) for the iteration history.

---

## The story this demo tells

> *"I'm going to Kyoto for 5 days next week — what about Buddy?"*

1. **Orchestrator** searches the Registry for a `plan_trip` skill → finds **TripPlanner**
2. **TripPlanner** builds a 5-day itinerary using Google Maps (Places API + Routes API)
3. TripPlanner notices "Buddy" → searches the Registry for `plan_walk` → finds **DogWalker**
4. **DogWalker** plans a daily routine (morning + afternoon walks to nearby parks)
5. TripPlanner stitches it all into one response

Four agents. Two protocols (A2A + MCP). One Registry. Zero hardcoded URLs.

---

## What's inside

| Folder | Role |
|---|---|
| [`discovery_agent/`](./discovery_agent/) | MCP discovery — finds and invokes MCP tools via Registry |
| [`dog_walker_agent/`](./dog_walker_agent/) | A2A specialist: plans personalized dog walks |
| [`trip_planner_agent/`](./trip_planner_agent/) | A2A specialist: plans city trips |
| [`orchestrator_agent/`](./orchestrator_agent/) | A2A client: routes by Registry skill search |
| [`common/`](./common/) | Shared helpers: ADC auth, Registry client, A2A client |
| [`PLAN.md`](./PLAN.md) | Original design doc + phase plan |

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (for dependency management)
- A Google Cloud project with these APIs enabled:
  - Agent Registry (`agentregistry.googleapis.com`)
  - Vertex AI (`aiplatform.googleapis.com`)
  - Places API New (`places.googleapis.com`)
  - Routes API (`routes.googleapis.com`)
- `gcloud` CLI with the alpha component installed
- ADC credentials (`gcloud auth application-default login`)

## Setup

```bash
git clone ... agent_marketplace_demo
cd agent_marketplace_demo
uv sync
cp .env.example .env  # fill in your GOOGLE_CLOUD_PROJECT
gcloud auth application-default login
gcloud services enable \
  agentregistry.googleapis.com aiplatform.googleapis.com \
  places.googleapis.com routes.googleapis.com \
  --project=<your-project>
gcloud components install alpha
```

## Quick start (the demo, end-to-end)

```bash
./deploy/start_local.sh                    # starts both A2A servers + registers
uv run python orchestrator_agent/agent.py "Walk Buddy this afternoon at 24th and Mission SF"
uv run python orchestrator_agent/agent.py "Plan a 2-day trip to Lisbon, I love pastéis de nata"
uv run python orchestrator_agent/agent.py "Going to Kyoto for 5 days, what about Buddy while I am away?"
./deploy/stop_local.sh                     # tears down
./deploy/stop_local.sh --deregister        # also remove from Registry
```

For prod deployment to Vertex AI Agent Engine (with auto-registration), see [`deploy/agent_engine.md`](./deploy/agent_engine.md).

---

## Tutorial — 4 parts

Read this end-to-end and you'll understand what the Agent Registry is, what A2A is, and how they fit with MCP. Each part is runnable on its own.

### Part 1 — Your first A2A agent (DogWalker)

**What you'll learn:** how to expose any ADK agent over the A2A protocol with `to_a2a()`, and how `AgentSkill` declarations make an agent *discoverable*.

```bash
# Terminal 1: start DogWalker as an A2A server
uv run python dog_walker_agent/server.py
# → DogWalker A2A server starting at http://localhost:8001
```

```bash
# Terminal 2: inspect the agent card the Registry will scrape
curl -s http://localhost:8001/.well-known/agent-card.json | jq .
```

You'll see a structured card with three **skills** — `plan_walk`, `recommend_dog_park`, `check_walk_conditions`. Each has a description and tags. These are what the Registry indexes for skill-based search.

You can also call the agent directly without a client SDK:

```bash
uv run python dog_walker_agent/agent.py "Walk Buddy this afternoon at 24th and Mission SF"
```

The agent uses real APIs:
- **wttr.in** for weather
- **Google Maps Places API (New)** for nearby dog parks
- **Google Maps Routes API** for walking directions

The output is a real walk plan with real SF parks and a working Google Maps URL.

**> What if I skipped the agent card?** `to_a2a()` would auto-generate a minimal card from the agent's name. But the skills array would be empty — meaning the Registry has nothing to index. Other agents could never discover this one by capability.

---

### Part 2 — Register the agent in the Agent Registry

**What you'll learn:** how to put an A2A agent into the Google Cloud Agent Registry so other agents can discover it. (In production, this happens automatically when you deploy to Agent Runtime — Phase 7. For local dev we register manually.)

With DogWalker still running on `localhost:8001`:

```bash
uv run python dog_walker_agent/register.py
# → ✓ Registered. Resource name:
#   projects/<your-project>/locations/global/services/dog-walker-agent
```

This calls `gcloud alpha agent-registry services create` with the agent card you saw in Part 1. The Registry scrapes the card and **auto-indexes all three skills**:

```bash
gcloud alpha agent-registry agents list --location=global --project=<your-project>
# → shows: dog-walker-agent with skills plan_walk, recommend_dog_park, check_walk_conditions
```

**> What if I skipped registration?** The agent runs fine, but no other agent can find it. The whole point of the Registry is to remove hardcoded URLs from your code.

---

### Part 3 — Discover and call a remote agent (Orchestrator)

**What you'll learn:** how an agent uses the Registry MCP server to find peer agents by skill, then dispatches via A2A. The Registry is itself an MCP server — agents discover other agents the same way they discover tools.

```bash
uv run python orchestrator_agent/agent.py "Walk Buddy this afternoon at 24th and Mission SF"
```

Watch the tool trace:

```
→ registry_search_agents(searchString='dog walking') → found dog-walker-agent
→ call_remote_a2a_agent(agent_resource_name='...services/dog-walker-agent',
                        message='Walk Buddy this afternoon...')
   ← DogWalker's plan
```

The orchestrator has **no idea where DogWalker lives**. It learns from the Registry, fetches the agent card to build an A2A client, sends the message, and returns the response.

**Key code** (in [`orchestrator_agent/agent.py`](./orchestrator_agent/agent.py)):

```python
registry_mcp_toolset = McpToolset(...)  # adds registry_* tools

async def call_remote_a2a_agent(agent_resource_name, message):
    info = registry.get_agent_info(agent_resource_name)
    url = info["protocols"][0]["interfaces"][0]["url"]
    # ... fetch card, create A2A client, send message ...
```

**> What if I hardcoded the URL?** It works until the agent moves, scales, or you deploy to a different environment. Registry-driven discovery is what makes the system robust to deployment changes.

---

### Part 4 — Two protocols, one Registry (Trip + Pet care)

**What you'll learn:** how MCP and A2A coexist, and how peer-to-peer delegation works between A2A agents.

Start the second specialist:

```bash
# Terminal 3
uv run python trip_planner_agent/server.py    # localhost:8002
uv run python trip_planner_agent/register.py  # add to Registry
```

Now the orchestrator routes both kinds of requests based purely on what's in the Registry:

```bash
uv run python orchestrator_agent/agent.py "Plan a 2-day trip to Lisbon, I love pastéis de nata"
# → Orchestrator finds TripPlanner via Registry → real Lisbon itinerary
```

Now the climax — **peer-to-peer**:

```bash
uv run python orchestrator_agent/agent.py "Going to Kyoto for 5 days next week, I love temples. What about Buddy while I am away?"
```

Trace:

```
Orchestrator
  → registry_search_agents("trip") → TripPlanner
  → call_remote_a2a_agent(TripPlanner, [verbatim user message])

TripPlanner (running on :8002, called over A2A)
  → get_weather, find_attractions, get_walking_route → 5-day Kyoto plan
  → noticed "Buddy" → registry_search_agents("dog") → DogWalker
  → call_remote_a2a_agent(DogWalker, "Arrange walks for Buddy June 1–5")

DogWalker (running on :8001, called over A2A)
  → get_dog_profile, get_weather, find_dog_parks → daily routine plan

← Combined response back to Orchestrator → user
```

Three agents, three discoveries, all via Registry. The Orchestrator never knows DogWalker exists — TripPlanner finds it autonomously.

**> What if MCP and A2A were the same thing?** They aren't, and that's the point. MCP is for *tools* (functions). A2A is for *agents* (colleagues with reasoning). The Registry holds both kinds of resources, so the discovery API is uniform even though what gets returned is different.

---

## Architecture diagram

```
User
 │ "Going to Kyoto, what about Buddy?"
 ▼
OrchestratorAgent ─────► Registry.search_agents("trip")
       │                          │
       │                          ▼
       │                  ┌────────────────┐
       └────────────────► │ Agent Registry │ ◄────┐
                          └────────────────┘      │ auto-register
                          ▲       ▲       ▲      │ on deploy
                          │       │       │      │
              ┌───────────┴───┐ ┌─┴────┐ ┌┴───────────┐
              │ DiscoveryAgent │ │DogWlk│ │TripPlanner │
              │ (MCP discovery)│ │ A2A  │ │    A2A     │
              └───────────────┘ └──┬───┘ └─────┬──────┘
                                   │           │
                                   │  peer-to-peer
                                   │ ◄─────────┘
                                   ▼
                          Google Maps APIs (ADC, no key)
                          wttr.in (weather)
```

---

## File index

| File | Phase | Purpose |
|---|---|---|
| [`pyproject.toml`](./pyproject.toml) | 0 | uv-managed dependencies |
| [`common/auth.py`](./common/auth.py) | 0 | Dynamic OAuth headers for ADC |
| [`common/registry_client.py`](./common/registry_client.py) | 0 | Thin AgentRegistry wrapper |
| [`common/a2a_client.py`](./common/a2a_client.py) | 5 | Shared `call_remote_a2a_agent` helper |
| [`dog_walker_agent/tools.py`](./dog_walker_agent/tools.py) | 1 | Weather + Maps tools (ADC, no key) |
| [`dog_walker_agent/agent.py`](./dog_walker_agent/agent.py) | 1 | LlmAgent + instructions |
| [`dog_walker_agent/agent_card.py`](./dog_walker_agent/agent_card.py) | 2 | A2A skills declaration |
| [`dog_walker_agent/server.py`](./dog_walker_agent/server.py) | 2 | `to_a2a()` + uvicorn |
| [`dog_walker_agent/register.py`](./dog_walker_agent/register.py) | 3 | Register service in Registry |
| [`trip_planner_agent/*`](./trip_planner_agent/) | 4 | Mirror of dog_walker for trips |
| [`orchestrator_agent/agent.py`](./orchestrator_agent/agent.py) | 3 | Strict pass-through router |
| [`discovery_agent/agent.py`](./discovery_agent/) | — | MCP discovery (adapted from upstream demo) |

---

## Why this demo is interesting

Most A2A tutorials hardcode the remote agent's URL. That works for a single example but doesn't tell you how a real agent ecosystem stays composable. This demo shows the full picture:

- **Skills are the discovery primitive**, not agent names — capabilities can be re-implemented or substituted without callers changing code.
- **The Registry holds both MCP servers and A2A agents** — one catalog, two protocols.
- **Peer-to-peer delegation** is just an agent doing what the orchestrator did — the protocol scales recursively.
- **Auto-registration on deploy** (Phase 7) means production agents appear in the Registry without any extra code.
