# Presentation Flow — A2A + Agent Registry with ADK

A ~25-minute tech talk that builds from "why" to "wow" using the agent_marketplace_demo as the running example.

## Audience & goal

**Who:** developers who've heard about agents but don't yet understand A2A or Agent Registry.

**What they should walk away knowing:**
- What an ADK agent looks like in code
- Why A2A exists and how it works (agent card, skills, JSON-RPC)
- What the Agent Registry is (and what it isn't)
- How A2A + Registry connect to enable capability-based discovery
- Where MCP fits in (tools vs agents)

**The one sentence the audience should remember:**

> *"The Agent Registry lets agents find each other by capability, so I can replace, redeploy, or add agents without touching anyone else's code."*

---

## Total runtime

| Section | Time |
|---|---|
| 0. Opening: race-condition shows the gap | 5 min |
| 1. ADK — the building block | 3 min |
| 2. The collaboration problem | 1 min |
| 3. A2A — agents talking to agents | 5 min |
| 4. The discovery problem (show the pain) | 2 min |
| 5. Agent Registry — the catalog | 5 min |
| 6. The climax — peer-to-peer in action | 5 min |
| 7. What this unlocks (+ race-condition callback) | 4 min |
| 8. Closing + Q&A | 1+ min |
| **Total** | **~30 min** |

---

## Pre-show checklist

```bash
cd /Users/annie/Documents/Demo/agent_marketplace_demo
./deploy/start_local.sh                                    # both A2A servers + register
uv run adk web . --port 8765 > .cache/adk_web.log 2>&1 &   # ADK web on 8765
```

For the race-condition opening (Section 0), pick ONE of these visuals to have ready:
- **Cached replay** (low-risk): run race-condition's local replay if you've cloned it — it streams NDJSON, no LLM calls, can't fail mid-demo
- **Pre-recorded video segment** (lowest-risk): grab a 30–60 sec clip from the Cloud Next '26 keynote (look in the `race-condition` repo's `docs/` or YouTube)
- **Banner image only** (fallback): the `race-condition/docs/images/banner.png` plus the architecture slide is enough if visuals aren't critical

Open browser tabs in this order (left-to-right in your tab bar):
1. Your slides (incl. race-condition banner + architecture diagram in Section 0)
2. ADK Web → http://localhost:8765
3. A2A Inspector → https://a2ainspect.com/ (or local Docker copy if presenting via Zoom)
4. Agent Registry console → https://console.cloud.google.com/agent-platform/agent-registry?project=neon-emitter-458622-e3
5. Terminal (in the project dir, ready to run commands)
6. (Optional) race-condition local instance or video tab

Have a backup screenshot/recording of a successful Test 4 run in case the live demo flakes.

> See [INTEGRATING_WITH_RACE_CONDITION.md](./INTEGRATING_WITH_RACE_CONDITION.md) for deeper context on why race-condition is the right "before" example and how the two demos relate.

---

## Section 0 — Opening: race-condition shows the gap (5 min)

### Slide: "You built an agent. Now what?"

**Say:**
> *"Show of hands — how many of you have built an agent in the last 6 months? Keep your hand up if your agent can talk to another agent — built by someone else, in a different framework, deployed somewhere you don't control."*
>
> *"Right. That's the gap. Let me show you what production-scale A2A actually looks like in 2026 — and what's still missing."*

### Slide: race-condition title + banner

> Visual: race-condition banner image (from `race-condition/docs/images/banner.png`)
> Subtitle: *"Open-sourced after Google Cloud Next '26 Developer Keynote"*

**Say:**
> *"This is `race-condition`. It's the open-source release of the multi-agent simulation Google demoed at Cloud Next '26 — a marathon in Las Vegas. Three agent types, all reasoning autonomously, all coordinating over A2A:"*
>
> - *"A **Planner** designs the race course using Google Maps, GIS tools, and a bit of financial modeling."*
> - *"A **Simulator** runs the environment tick-by-tick — weather, traffic, crowds."*
> - *"And **Runner** agents — NPCs — each decide their own pacing, hydration, strategy as the race unfolds. Hundreds of them."*

### 🎬 Demo: race-condition visual (30–60 sec)

Show ONE of:
- **Cached replay** — race-condition has a built-in NDJSON replay mode, indistinguishable from a live session, can't fail mid-demo
- **Pre-recorded keynote clip** — 30–60 sec from the Cloud Next '26 Developer Keynote
- **Static screenshot of the 3D Angular/Three.js frontend** — if visuals aren't critical

**Say while it runs:**
> *"Every dot is an agent reasoning in real time. The frontend is Angular and Three.js. Every Runner is its own LLM-driven process. This is what A2A at production scale looks like."*

### Slide: race-condition architecture

```
        Frontend (Angular + Three.js)
                │
                ▼
         Go Hub Gateway ◄─── WebSocket routing, batching, fan-out
                │
                ├── A2A ──► Planner    (course design)
                ├── A2A ──► Simulator  (environment ticks)
                └── A2A ──► Runner × N (per-NPC decisions)
                                │
                                └── MCP ──► Maps tools
                                       (discovered via Agent Registry)
```

**Say (this slide is the setup for the rest of the talk — slow down):**
> *"Look closely at how the agents are connected. The Go Hub in the middle routes A2A traffic — every WebSocket message, every batch, every fan-out. It knows where the Planner lives. It knows where every Runner lives."*
>
> *"And notice one detail — the Agent Registry IS in this picture, but only on the right. It's used for one thing: discovering the Maps MCP server. For the **agents themselves**, the Hub holds the URLs."*

### Slide: 🎯 The gap

> race-condition uses **Agent Registry for MCP tool discovery** ✅
>
> race-condition uses **the Hub** (with known URLs) **for A2A agent routing** ❌

**Say:**
> *"This is the gap I want to teach today. A2A solved the wire problem — any agent can call any agent over a standard protocol. But for race-condition, **discovery of the agents themselves is still hardcoded**. Add a 100th runner type. Let another team ship a heat-adapted runner variant. The Hub needs to know about it."*
>
> *"What if the agents themselves were discoverable through the Registry — the same way Maps MCP already is? That's the question this talk answers. I'll build it up with a smaller, simpler demo, and at the end come back to race-condition and show you the line we'd add."*

### Slide: today's agenda

A simple list:
1. ADK — what an agent looks like in code
2. A2A — agents talking to agents (the wire)
3. The discovery problem — show the pain in code
4. Agent Registry — capability-based discovery
5. The climax — 3 agents collaborating, no hardcoded URLs
6. Tie it back to race-condition

**Say:**
> *"Five build-ups and one callback. Let's go."*

---

## Section 1 — ADK, the building block (3 min)

### Slide: "An agent = LLM + tools + reasoning loop"

Show a tiny code block:

```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini

agent = LlmAgent(
    model=Gemini(model="gemini-3-flash-preview"),
    name="dog_walker",
    instruction="...",
    tools=[get_dog_profile, get_weather, find_dog_parks, get_walking_route],
)
```

**Say:**
> *"This is ADK — Google's Agent Development Kit. Open source, cross-language (Python, Go, Java, TypeScript). It graduated to 1.0 GA earlier this year."*
>
> *"What is an agent? It's an LLM plus tools plus a reasoning loop. The model decides which tool to call, you execute it, the result feeds back into the model. ADK gives you the SDK and the loop."*

### 🎬 Demo: ADK Web — see the reasoning loop

1. Switch to ADK Web tab (http://localhost:8765)
2. Pick `dog_walker_agent` from the dropdown
3. Click **+ New Session**
4. Type: *"Walk Buddy this afternoon at 24th and Mission SF"*
5. **Narrate as tool events appear** (right panel):

> *"It's calling get_dog_profile — learning that Buddy is a high-energy Lab... now get_weather — pulling real-time SF weather from wttr.in... find_dog_parks — Google Maps Places API, returning real SF parks... and get_walking_route — building an actual walking route."*

6. When the response lands:

> *"That's a real plan. Real parks, real walking time, real Google Maps URL. The agent reasoned about Buddy's heat tolerance, the current weather, and the time of day."*

### Slide: "Why this matters"

**Say:**
> *"This is the new primitive. Where 5 years ago we glued APIs together by hand, we now have agents that reason. But notice — this agent only exists on my laptop. No one else can use it. That's the next problem."*

**Transition:**
> *"So how do we make this agent usable by others? Could I bake it into another agent as a sub-agent? Sure, but then they're tied at the hip — same process, same deploy, same team. That doesn't scale. We need a wire protocol."*

---

## Section 2 — The collaboration problem (1 min)

### Slide: "The two ways agents can talk"

| Option | Pro | Con |
|---|---|---|
| In-process sub-agent | Fast, easy | Tightly coupled. One team, one deploy. |
| Network call (hardcoded URL) | Decoupled processes | URL changes break callers. No discovery. |

**Say:**
> *"For agents to be reusable across teams and orgs, we need them to be network services. But just exposing an HTTP endpoint isn't enough — we need a standard protocol so any framework can call any framework. That's A2A."*

---

## Section 3 — A2A: agents talking to agents (5 min)

### Slide: "A2A — Agent-to-Agent Protocol"

Three bullets:
- **Open protocol** — JSON-RPC 2.0 over HTTP
- **Cross-framework** — works with ADK, LangGraph, CrewAI, AutoGen, Semantic Kernel
- **Donated to Linux Foundation** — 150+ orgs in production (Google, Microsoft, AWS, Salesforce, IBM…)

**Say:**
> *"A2A is to agents what HTTP is to websites. A standard wire protocol so anyone can call anyone, regardless of framework, vendor, or language. It's how you turn an agent into a microservice."*

### Slide: "The Agent Card — the discovery contract"

**Say:**
> *"Every A2A agent serves a JSON document at slash dot-well-known slash agent-card.json. That document is the agent's contract — its name, version, URL, and crucially, its **skills**."*

### 🎬 Demo: curl the agent card

```bash
curl -s http://localhost:8001/.well-known/agent-card.json | jq .
```

Audience sees the JSON. Point at the **skills array** specifically:

```json
"skills": [
  { "id": "plan_walk", "tags": ["dog", "walk", "route", ...], "description": "..." },
  { "id": "recommend_dog_park", ... },
  { "id": "check_walk_conditions", ... }
]
```

**Say:**
> *"Three skills. Each has an ID, a description, and tags. **This is the discovery primitive** — when another agent wants to find someone who can plan a dog walk, this is what it searches against."*

### Slide: "Wrapping an ADK agent as A2A — one line"

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

app = to_a2a(my_agent, host="localhost", port=8001, agent_card=card)
# Then: uvicorn module:app
```

**Say:**
> *"In ADK, exposing an agent over A2A is literally one function call. `to_a2a` returns a Starlette app you run with uvicorn. The framework handles all the JSON-RPC protocol details."*

### 🎬 Demo: A2A Inspector — see the wire protocol

1. Switch to A2A Inspector (a2ainspect.com)
2. Enter `http://localhost:8001` → click Connect
3. Show the **Agent Card tab** — same JSON as the curl, but rendered nicely
4. Switch to **Chat tab**, send: *"Walk Buddy this afternoon at 24th and Mission SF"*
5. While it runs, switch to the **Console tab**

**Say:**
> *"Watch the right panel. That's the raw JSON-RPC traffic — messages going out, responses coming back. This is A2A on the wire. Anyone with an HTTP client can do this. A LangGraph agent could call this exact endpoint."*

### Slide: "What we have so far"

- ✅ An agent we can run locally (ADK)
- ✅ A standard wire protocol (A2A)
- ✅ A self-describing contract (agent card with skills)
- ❌ Anyone calling it still needs to know the URL

**Transition:**
> *"This is where most A2A tutorials stop. They show you `to_a2a`, they hardcode the URL, you're done. But hardcoded URLs don't scale. So how does anyone *find* this agent?"*

---

## Section 4 — The discovery problem: show the pain (2 min)

> This is the key transition slide. Don't skip it — the audience needs to feel the pain before they appreciate the Registry.

### Slide: "A2A gives us the wire. But who do we call?"

**Say:**
> *"OK we have A2A. Any agent can call any other agent over a standard protocol. Great. But here's the question that doesn't have an answer yet: how does the orchestrator know that TripPlanner and DogWalker even exist?"*
>
> *"Let me show you what the orchestrator would have to look like with A2A alone — no Registry, just URLs."*

### Slide: "Orchestrator without a Registry"

```python
# Without Agent Registry — everyone hardcodes everything
TRIP_PLANNER_URL  = "http://localhost:8002"
DOG_WALKER_URL    = "http://localhost:8001"
FLIGHT_AGENT_URL  = "http://flights.internal/"
SUPPORT_AGENT_URL = "http://support.internal/"
# ... 50 more

def route(user_msg: str) -> str:
    if "trip" in user_msg or "kyoto" in user_msg or "vacation" in user_msg:
        return call_a2a(TRIP_PLANNER_URL, user_msg)
    elif "buddy" in user_msg or "dog" in user_msg or "walk" in user_msg:
        return call_a2a(DOG_WALKER_URL, user_msg)
    elif "flight" in user_msg or "fly" in user_msg:
        return call_a2a(FLIGHT_AGENT_URL, user_msg)
    elif ...
```

**Say:**
> *"This is what every A2A orchestrator looks like without a Registry. Hardcoded URLs. Hardcoded if/elif chains. And the pain is:"*

### Slide: "What breaks"

Four bullets:
- 🛠️ **New agent ships → update this file** (and redeploy the orchestrator)
- 🚚 **Agent URL changes (staging → prod) → broken**
- 🤷 **Two agents do similar things → orchestrator has to encode "which one"**
- 🔍 **Someone in another team built the perfect agent → you don't know it exists**

**Say:**
> *"This is the configuration tax. Every new agent makes every orchestrator slightly more brittle. It doesn't scale past a handful of agents."*

### Slide: "What we actually want"

```python
# With Agent Registry — capability-based discovery
agents = registry.search_agents("plan a trip")
return call_a2a(agents[0].url, user_msg)
```

**Say:**
> *"Two lines. The orchestrator doesn't know names. Doesn't know URLs. Doesn't know who's out there. It just says: 'who can do X?'"*

### Slide: 💡 The "aha"

> **Registry is the difference between hardcoded routing and capability-based routing.**
>
> From `if/elif/else` chains to `"who can do X?"` queries.
>
> - New agents become discoverable the moment they register.
> - Old agents disappear gracefully.
> - Multiple matches? Registry returns all of them. Caller picks.

**Say (slow this one down — it's the punchline of the whole talk):**
> *"This is the shift. From the orchestrator owning a config of all the world's agents — to the orchestrator asking the world a question. That's the difference the Registry makes."*

---

## Section 5 — Agent Registry: the catalog (5 min)

### Slide: "Google Cloud Agent Registry"

Three bullets:
- **A catalog**, not a runtime — stores metadata (name, URL, skills), not the agent itself
- **Holds both A2A agents AND MCP servers** — one place for all discoverable resources
- **Auto-indexes skills** from each agent's card

**Say:**
> *"Critical distinction up front: the Agent Registry is a catalog, not a runtime. It stores pointers. The URL it stores can be anywhere — Cloud Run, Agent Engine, your laptop, a tunnel to on-prem. Doesn't matter. The Registry just remembers the address."*

### Slide: "Two ways to register"

| Method | When | URL points to |
|---|---|---|
| Manual: `gcloud agent-registry services create` | Local dev, on-prem | Anything you tell it |
| Auto: deploy to Vertex AI Agent Engine | Production | The deploy's URL |

**Say:**
> *"This is the misconception that trips people up: 'agents only appear in the Registry if I deploy to Agent Engine.' False. Agent Engine deploy is one way to populate the Registry. Manual `gcloud agent-registry services create` is another — works fine for local dev, and that's how this demo's agents got registered."*

### 🎬 Demo: see them in the console

1. Switch to the Agent Registry console tab
2. Show the list — `dog_walker_agent`, `trip_planner_agent`
3. Click into `dog_walker_agent`

Point at:
- Protocol: A2A_AGENT
- Interface URL: `http://localhost:8001/` (audience reaction shot — "wait, localhost?!")
- The three skills with their descriptions and tags

**Say:**
> *"The URL is literally localhost. The Registry doesn't know or care. It just stores what I told it. And look — the skills got auto-indexed when the agent card was scraped. The Registry now knows this agent can `plan_walk`, `recommend_dog_park`, `check_walk_conditions`."*

### Slide: 💡 "Skills = yellow pages, not phone book"

> Without skills, the Registry would be a phone book — you have to know the name to look something up.
>
> With skills, it's yellow pages — you say *"I need someone who can plan a walk"* and the right agent answers, even if you've never heard of it.

**Say:**
> *"This is why skills aren't a nice-to-have — they're the whole point. The orchestrator never knew TripPlanner's name. It just said 'plan a trip,' and the Registry returned the right agent. Add a flight-booking agent tomorrow with a `book_flight` skill — the orchestrator finds it the moment someone asks about flights, without a single code change."*

### Slide: "MCP — the other half"

> Audience may be wondering "what about MCP — isn't that for tools?"

**Say:**
> *"Quick aside on MCP — Model Context Protocol. MCP is the standard for an agent calling tools. A2A is for an agent calling other agents. Same idea — open protocol — different scope."*
>
> *"And here's the elegant part: the Agent Registry is **itself an MCP server**. The Registry exposes tools like `search_agents`, `list_agents`, `get_agent` over MCP. So your agents discover other agents using the same mechanism they use to discover tools."*

### Slide: "Where MCP shows up in this demo"

| Use of MCP | How it appears |
|---|---|
| **Registry MCP** *(used)* | The orchestrator's `registry_search_agents` is an MCP tool call against `agentregistry.googleapis.com/mcp` |
| **Maps MCP** *(not used here)* | This demo calls Google Maps **directly** via REST + ADC for simplicity. In a "pure" version, Maps would be discovered as an MCP server in the Registry and called over MCP — making it swappable for, say, OpenStreetMap MCP with zero code changes. |

**Say (honest disclosure):**
> *"Quick honest note — we use MCP for the Registry, but for Google Maps we cheated and called it directly. The reason: less moving parts in this demo. But the principle stands — if Maps were registered as an MCP server, we could swap it for OpenStreetMap by updating a single Registry entry, no code changes. That's the MCP value: standardized, swappable, discoverable tool servers."*

### 🎬 Optional demo: list Registry MCP tools

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
            headers=get_dynamic_headers()),
        header_provider=get_dynamic_headers)
    for t in await ts.get_tools(): print(' -', t.name)

asyncio.run(main())
"
```

**Say:**
> *"20+ tools. `search_agents`, `list_agents`, `get_agent`, `list_mcp_servers`. MCP and A2A coexist. Registry holds both."*

### Slide: "How A2A + Registry connect"

A simple diagram:

```
Agent B needs help
        │
        ▼
Agent B → Registry.search_agents("plan a trip")
        │
        ├─ Registry returns: trip-planner-agent + URL
        │
        ▼
Agent B → A2A call to that URL  →  Agent A (trip planner)
        │
        ◄── A2A response
```

**Say:**
> *"This is the connection. Skills get registered. Agents search by capability. Once they find a match, they call via A2A. Zero hardcoded URLs."*

---

## Section 6 — The climax: peer-to-peer (5 min)

### Slide: "Putting it all together"

> *"Three agents in this demo. One Orchestrator, two specialists. None of them know each other's URLs. Watch what happens when I give the Orchestrator a request that needs both specialists."*

### 🎬 Demo: the full peer-to-peer chain

1. Switch to ADK Web → pick `orchestrator_agent` → **+ New Session**
2. Type: *"Going to Kyoto for 5 days, what about Buddy while I am away"*
3. **Narrate the trace as events appear** (this is the magic moment — slow down and explain):

> *"Event 1 — Orchestrator searches the Registry for 'trip planning.'"*
>
> *"Event 2 — Registry returns trip-planner-agent. Orchestrator now has a resource name."*
>
> *"Event 3 — Orchestrator sends the user's exact message to TripPlanner over A2A. It's forwarding verbatim — including the 'what about Buddy' part."*
>
> *"TripPlanner is now reasoning. It calls Google Maps for Kyoto attractions, plans a 5-day itinerary..."*
>
> *"And here's the moment — TripPlanner sees 'Buddy' in the message. It searches the Registry for 'dog.'"*
>
> *"Registry returns dog-walker-agent. TripPlanner calls it via A2A — agent calling agent."*
>
> *"DogWalker plans Buddy's daily routine, returns it."*
>
> *"TripPlanner stitches everything together — Kyoto itinerary + Buddy's care — and returns one response."*

4. Final response renders — point at it:

> *"Three agents collaborated. Two protocols (A2A + MCP) coexisted. Zero hardcoded URLs in any of them. If I added a flight-booking agent tomorrow and registered it, the orchestrator would discover and route to it the moment it appeared in the catalog."*

### Slide: "What just happened (visually)"

```
You
 │
 ▼
Orchestrator ── search Registry → finds TripPlanner ── A2A call ──┐
                                                                  ▼
                                                            TripPlanner
                                                                  │
                                                                  │ search Registry
                                                                  │ → finds DogWalker
                                                                  │
                                                                  ├── A2A call ──→ DogWalker
                                                                  │                    │
                                                                  ◄────── A2A ─────────┘
                                                                  │
                                                                  ▼
                                                          combined response
```

---

## Section 7 — What this unlocks (3 min)

### Slide: "Why this matters"

Three bullets — for each, say one sentence:

- **Different teams own different agents** — *"Your trip-planning team and your dog-walking team don't need to know each other exist. They publish to the Registry; consumers find them by skill."*
- **Replace, scale, redeploy without breaking callers** — *"DogWalker v2 hits the Registry, v1 goes away — callers don't change a line of code. That's the discovery-by-capability win."*
- **Cross-framework interop** — *"This demo is all ADK. But the same Registry could hold LangGraph agents, CrewAI agents, custom-built A2A servers. The protocol is open. The catalog is uniform."*

### Slide: "What you'd lose without each piece"

| Piece | Without it | With it |
|---|---|---|
| **A2A** | Bespoke integration per agent pair. Framework lock-in. | One wire protocol; any framework calls any framework. |
| **Agent Registry** | Hardcoded URLs. New agents invisible. `if/elif` routing. | Capability-based discovery. New agents auto-found by skill. |
| **Skills** | Phone book — must know the agent's name to find it. | Yellow pages — say *what you need*, get the right agent. |
| **MCP** | Custom code for every tool integration. | Standard tool protocol. Tools become catalogable and swappable. |

**Say:**
> *"Each piece is independently useful. **A2A alone** = standard protocol but you still hardcode URLs. **A2A + Registry** = dynamic discovery but you still need agent names. **A2A + Registry + Skills** = full capability-based composition. **Plus MCP** = the same story extends to tools, not just agents."*
>
> *"Take any piece out and the system regresses. Together, you get a composable agent ecosystem."*

### Slide: 🔁 Callback — apply this to race-condition

> Remember the architecture from the opening:
>
> ```
> Go Hub  ──► A2A ──► Planner / Simulator / Runners
>             (Hub holds every URL)
> ```
>
> What if the Hub didn't hardcode anything?
>
> ```
> Go Hub  ──► Registry.search_agents("runner") ──► any registered runner
>             (any team can publish; Hub finds them)
> ```

**Say (this is the closing tie-back — make it land):**
> *"This is the lever. race-condition already uses Registry for MCP tools — that's how it finds Maps. The **exact same pattern** applied to A2A agents means: any team in the company can ship a new runner variant — heat-adapted, sprint-finish, dietary-strategy — and the Hub picks it up the moment it's registered. No Hub code changes."*
>
> *"That's the dream we just demoed at toy scale. Race-condition is the production-scale chassis. Together they show the full picture: A2A is the wire, Registry is the discovery, MCP is the tools — and applied consistently, you get an agent ecosystem instead of a wiring project."*

### Slide: "The 2026 multi-agent stack"

```
┌─────────────────────────────────────────────────────────┐
│ Agent Registry (catalog: agents + MCP servers + skills) │
└─────────────────────────────────────────────────────────┘
              ▲                          ▲
              │ skill-based discovery    │
              │                          │
┌─────────────┴────────────┐  ┌──────────┴──────────────┐
│   A2A (agent → agent)    │  │   MCP (agent → tool)    │
└──────────────────────────┘  └─────────────────────────┘
              ▲                          ▲
              │                          │
┌─────────────┴──────────────────────────┴────────────────┐
│         ADK (build, deploy, run agents in code)         │
└─────────────────────────────────────────────────────────┘
```

**Say:**
> *"This is the stack to watch. ADK at the bottom — how you build. MCP and A2A in the middle — how things talk. Registry on top — how things are found. Each piece is open. Each replaceable."*

---

## Section 8 — Closing + Q&A (1+ min)

### Slide: "One sentence to remember"

> *"The Agent Registry lets agents find each other by capability, so I can replace, redeploy, or add agents without touching anyone else's code."*

### Slide: "Where to start"

- ADK docs: https://adk.dev
- A2A spec: https://a2a-protocol.org
- This demo: `github.com/<you>/agent_marketplace_demo`

---

## Q&A — what you'll likely get asked

| Q | Concise answer |
|---|---|
| "What's the difference between MCP and A2A?" | MCP = call a tool (function). A2A = talk to an agent (colleague with reasoning). |
| "Why not just use sub-agents in ADK?" | Same-process sub-agents are tightly coupled. A2A is for cross-team, cross-deploy, cross-framework. Think microservices vs. monolith. |
| "Can a LangGraph agent call my ADK agent?" | Yes — that's literally the point of A2A. The wire protocol is framework-agnostic. |
| "How do agents authenticate?" | A2A supports OAuth bearer tokens, API keys, and service-account auth. The agent card declares supported schemes. |
| "Does this work outside Google Cloud?" | A2A and MCP are open and framework/cloud-agnostic. The Agent Registry is Google Cloud's catalog implementation; other clouds will likely follow with their own catalogs. |
| "What's the cost?" | Agent Registry is free for storage. You pay for the underlying compute (Vertex AI, Agent Engine, Cloud Run, etc.) where the agents actually run. |
| "How do I deploy this for real?" | `adk deploy agent-engine` packages your ADK agent and deploys to Vertex AI Agent Engine, which auto-registers it in the Registry. See [`deploy/agent_engine.md`](./deploy/agent_engine.md). |
| "What if two agents have the same skill?" | The Registry returns all matches. The caller decides — by name, version, deployment, latency, etc. You can also use bindings to scope which agents can call which others. |
| "How would I apply this to race-condition?" | Today, race-condition's Hub holds A2A agent URLs and uses Registry only for Maps MCP. The pattern from this demo would replace the Hub's hardcoded URLs with `registry_search_agents("runner")` calls. Any team's runner variant would become discoverable on registration — no Hub code changes. See [INTEGRATING_WITH_RACE_CONDITION.md](./INTEGRATING_WITH_RACE_CONDITION.md). |
| "Why is this called Agent Registry and not [some other name]?" | It's a yellow-pages-style catalog. The name reflects what it does: register and discover. |

---

## If the live demo fails

Don't panic. Have ready:

1. **Screenshots** of a successful Test 4 run (the orchestrator's trace + final response)
2. **A pre-recorded screen capture** of the full peer-to-peer chain
3. **Fallback narrative**: *"The live API is having a moment — here's what should have happened…"* Walk through the screenshots.

Common failure modes and recovery:
- **Network slow → demo times out**: switch to recording. Audience won't care.
- **Maps API quota exceeded**: same — switch to recording.
- **Wrong session in ADK Web**: click **+ New Session** to reset state.
- **Server died**: open a new terminal, `./deploy/start_local.sh`, wait 10s, retry.

---

## One-page cheat sheet (print or have on a second screen)

```
PRE-SHOW
  cd /Users/annie/Documents/Demo/agent_marketplace_demo
  ./deploy/start_local.sh
  uv run adk web . --port 8765 &
  Open tabs: slides | ADK Web | A2A Inspector | Registry Console | Terminal
  Have race-condition visual ready (cached replay, video clip, or banner image)

ACT 0 (5 min) — RACE-CONDITION SHOWS THE GAP
  Slide: "You built an agent. Now what?" — hands-up question
  Slide: race-condition banner — Cloud Next '26 keynote demo
  SAY: "Planner + Simulator + hundreds of Runners, all over A2A"
  Demo: race-condition visual (replay / video / screenshot)
  Slide: architecture diagram (Hub routes A2A; Registry only used for Maps MCP)
  Slide: 🎯 The gap — Registry only for MCP, agents are Hub-routed
  SAY: "What if agents themselves were Registry-discovered? That's today's question."
  Slide: agenda (5 build-ups + 1 callback)

ACT 1 (3 min) — ADK
  ADK Web → dog_walker_agent → "Walk Buddy this afternoon at 24th and Mission SF"
  POINT AT: tool calls happening live
  SAY: "LLM + tools + reasoning loop. ADK gives us the SDK."

ACT 2 (1 min) — collab problem
  SAY: "Hardcoded URLs don't scale. We need a standard protocol."

ACT 3 (5 min) — A2A
  curl http://localhost:8001/.well-known/agent-card.json | jq .
  POINT AT: skills array
  Switch to A2A Inspector → http://localhost:8001 → send message
  POINT AT: console tab JSON-RPC traffic
  SAY: "Open protocol. Skills are the discovery primitive."

ACT 4 (2 min) — SHOW THE PAIN
  Slide: orchestrator code with hardcoded URLs + if/elif chains
  SAY: "Every new agent = update this file. This is the configuration tax."
  Slide: with Registry — 2 lines: search_agents("plan a trip") → call_a2a
  SAY (aha): "Hardcoded routing → capability-based routing. From if/elif to 'who can do X?'"

ACT 5 (5 min) — Registry
  Console → click dog_walker_agent → show skills, URL=localhost (reaction)
  SAY: "Catalog, not a runtime. Auto-indexes skills."
  Slide: 💡 Skills = yellow pages, not phone book.
  SAY: "Registry itself is an MCP server. MCP for tools, A2A for agents, same catalog."
  Honest note: "Maps in this demo = direct API. In a pure version, Maps would be MCP."

ACT 6 (5 min) — CLIMAX
  ADK Web → orchestrator_agent → "Going to Kyoto for 5 days, what about Buddy while I am away"
  NARRATE: search → delegate → TripPlanner reasons → peer-search → DogWalker → combine
  SAY: "3 agents, 0 hardcoded URLs."

ACT 7 (4 min) — what this unlocks + race-condition callback
  Slide: "Without each piece" table
  SAY: "A2A alone = standard protocol + hardcoded URLs. +Registry = discovery.
        +Skills = capability-based. +MCP = same story for tools."
  Slide: 🔁 Apply this to race-condition
  SAY: "Hub today: hardcoded URLs per agent type.
        Hub with this pattern: Registry.search_agents('runner').
        Any team's runner variant becomes discoverable on registration."

CLOSING (1 min)
  "race-condition is the chassis. This is the discovery layer.
   Together = agent ecosystem instead of wiring project."
  → Q&A
```
