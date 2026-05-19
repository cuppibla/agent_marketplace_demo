# Presentation Script — A2A + Agent Registry with ADK

A YouTube-style script for a ~35-minute tech talk. Production-grade: every file path, line number, URL, command, and click cue is spelled out so you (or a video producer) can follow it without improvising.

This file has three layers per slide:

- 🎬 **PRODUCTION** — operational steps: which file to open, which window to switch to, which command to run
- 🎙️ **NARRATION** — what to say (conversational prose, read it aloud)
- 💬 **ANTICIPATED QUESTIONS** — head off audience confusion inline

---

## Audience & goal

**Who:** developers who've heard about agents but don't yet understand A2A, Agent Registry, or how they fit with MCP.

**The one sentence to remember:**

> *"The Agent Registry lets agents find each other by capability, so I can replace, redeploy, or add agents without touching anyone else's code."*

---

## Total runtime

| Section | Time |
|---|---|
| 0. Opening: race-condition shows the gap | 7 min |
| 1. ADK — the building block | 3 min |
| 2. The collaboration problem | 1 min |
| 3. A2A — agents talking to agents | 5 min |
| 4. The discovery problem (live demo) | 3 min |
| 5. Agent Registry — the catalog | 5 min |
| 6. The climax — peer-to-peer in action | 5 min |
| 7. What this unlocks + race-condition callback | 4 min |
| 8. Closing + Q&A | 1+ min |
| **Total** | **~34 min** |

---

# 🖥️ Workspace setup — name your windows once, refer to them by name throughout

Set this up **before** the talk and don't move things during the talk. The script refers to these by short codes.

| Code | Window | What's open |
|---|---|---|
| **W-SLIDES** | Browser tab 1 (full-screen on output) | Your slide deck |
| **W-ADKWEB** | Browser tab 2 | http://localhost:8765 (ADK Web) |
| **W-INSPECTOR** | Browser tab 3 | https://a2ainspect.com/ (or local Docker copy) |
| **W-CONSOLE** | Browser tab 4 | https://console.cloud.google.com/agent-platform/agent-registry?project=neon-emitter-458622-e3 |
| **W-RACE** | Browser tab 5 *(optional)* | race-condition frontend at http://localhost:9119 — only if you spin it up |
| **W-EDITOR** | VS Code / Cursor window | Project root: `/Users/annie/Documents/Demo/agent_marketplace_demo/` |
| **W-TERM1** | Terminal 1 | Server lifecycle (start_local.sh, ADK web, etc.) |
| **W-TERM2** | Terminal 2 | Demo commands (curl, orchestrator runs) — keep clean for live demos |

---

# 🚀 Pre-show — run this exact sequence 5 minutes before going live

### Step 1 — Start servers (in W-TERM1)

```bash
cd /Users/annie/Documents/Demo/agent_marketplace_demo
./deploy/start_local.sh
```

This starts DogWalker on :8001 and TripPlanner on :8002 and registers both in the Agent Registry. Wait until you see "✓ Both agents are up and registered."

### Step 2 — Start ADK Web (in W-TERM1, second tab/pane)

```bash
cd /Users/annie/Documents/Demo/agent_marketplace_demo
uv run adk web . --port 8765
```

Wait until you see "ADK Web Server started" at http://localhost:8765.

### Step 3 — Verify everything's up (in W-TERM2)

```bash
curl -fs http://localhost:8001/.well-known/agent-card.json -o /dev/null && echo "✓ DogWalker"
curl -fs http://localhost:8002/.well-known/agent-card.json -o /dev/null && echo "✓ TripPlanner"
curl -fs http://localhost:8765/list-apps -o /dev/null && echo "✓ ADK Web"
```

You should see three checkmarks.

### Step 4 — Open all browser tabs (W-ADKWEB, W-INSPECTOR, W-CONSOLE, optionally W-RACE)

### Step 5 — Open W-EDITOR at these files (you'll switch to them mid-talk)

- `dog_walker_agent/agent.py` (will reference line 46 — the `LlmAgent(...)` call)
- `dog_walker_agent/agent_card.py` (will reference the `skills=[...]` list)
- `orchestrator_agent/agent.py` (Registry version)
- `orchestrator_agent/agent_without_registry.py` (no-Registry version — the "before" file)

### Step 6 (optional) — Spin up race-condition

Only do this if you want the optional curl in Act 3 to work, or you want to play a live visual instead of a recording in Act 0.

```bash
# In a third terminal pane (don't tangle with the demo servers):
cd /Users/annie/Documents/Demo/race-condition
make dev   # or whatever its top-level "start everything" command is
# Wait for http://localhost:9119 to load (the frontend)
# Wait for http://localhost:9105/.well-known/agent-card.json to return JSON
```

### Step 7 — Have a backup

Take a screen recording of a successful peer-to-peer run NOW. If the live demo in Act 6 fails, switch to the recording.

### Image assets you'll need in `assets/`

- `assets/race-condition-banner.png` — grab from race-condition's `docs/images/banner.png`
- `assets/race-condition-hybrid-transport.png` — Hybrid Transport Model diagram
- `assets/race-condition-a2a-topology.png` — A2A Network Topology diagram

---

# 🎬 ACT 0 — Race-condition shows the gap (7 min)

## Slide 0.1 — "You built an agent. Now what?"

🎬 **PRODUCTION**
- **W-SLIDES** — title slide is up
- (No file or terminal action yet)

🎙️ **NARRATION**

**(Wait for the audience to settle. Then start.)**

Let me start with a show of hands. How many of you have built an agent in the last six months? Just raise your hand.

OK, now keep your hand up if your agent talks to another agent — one built by someone else, in a different framework, deployed somewhere you don't control.

**(Most hands go down.)**

Right. That's the gap I want to talk about today. Everyone is building agents in 2026. Almost nobody has figured out how to make them collaborate, especially across teams. The bottleneck in your company a year from now won't be building agents — it'll be making them work together.

Today I want to show you the three pieces that fix this: **the A2A protocol**, **the Agent Registry**, and **MCP for tools**. We'll build them up together using a small demo, but before we do, I want to ground the conversation in something real you've probably seen.

---

## Slide 0.2 — race-condition banner

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the race-condition banner slide (with `assets/race-condition-banner.png`)
- Caption visible: *"race-condition — open-sourced after Google Cloud Next '26 Developer Keynote"*

🎙️ **NARRATION**

This is **race-condition**. It's the open-source release of the multi-agent simulation Google demoed at the Cloud Next '26 Developer Keynote earlier this year. It's a marathon in Las Vegas, but run entirely by AI agents.

Three agent types coordinate the whole thing:

- A **Planner** designs the race course using Google Maps, GIS analysis tools, and a bit of financial modeling — sponsorship costs, road closure budgets, that sort of thing.
- A **Simulator** runs the environment tick by tick. Weather changes. Traffic builds up at intersections. Crowds cheer at certain mile markers.
- **Runner agents** — these are the NPCs, the non-player-character runners — each decide their own pacing, when to drink water, when to push, when to back off. Hundreds of them, all reasoning independently.

All of this coordination happens over the A2A protocol — Agent-to-Agent. We'll define A2A in detail in a few minutes.

---

## Slide 0.3 — race-condition visual (30–60 sec)

🎬 **PRODUCTION** — pick ONE option, set up in advance:

| Option | Source | Reliability |
|---|---|---|
| **A. Cached replay (recommended)** | `race-condition`'s built-in NDJSON replay mode | Highest — can't fail mid-demo |
| **B. Pre-recorded keynote clip** | 30–60 sec clip from Cloud Next '26 Developer Keynote | High — pre-rendered video |
| **C. Live race-condition** | If W-RACE is up: switch to http://localhost:9119, click "Start simulation" | Lower — real network/LLM calls |
| **D. Static screenshot** | Just a screenshot of the 3D frontend | Fallback if visuals aren't critical |

Switch to the appropriate window for your chosen option. Let it play for 30–60 sec.

🎙️ **NARRATION** *(while it plays)*

What you're seeing is the simulator's tick stream rendering through a 3D Angular and Three.js frontend. Every dot moving on screen is an LLM-driven agent making its own decisions in real time. This is what A2A at production scale looks like.

Now, this is impressive. But it's not what this talk is about. This talk is about **the architectural choice** race-condition had to make to wire all these agents together — and the choice it didn't make.

🎬 **PRODUCTION** — when the visual ends, **switch back to W-SLIDES** to advance to the architecture diagram.

---

## Slide 0.4 — Hybrid Transport Model diagram

🎬 **PRODUCTION**
- **W-SLIDES** — advance to slide with `assets/race-condition-hybrid-transport.png`
- Have your laser pointer / cursor ready to point at specific boxes

📝 **NOTE FOR PRESENTER**: This slide is detail-heavy. If your audience is execs or PMs, skip to Slide 0.6. If engineers, this earns the production-scale claim.

🎙️ **NARRATION**

This is race-condition's actual transport architecture. Don't worry about memorizing it — I just want you to see three things.

**First**, three different protocols for three different jobs.

> 🔍 **POINT AT** the "WebSocket (binary protobuf)" arrow

Binary protobuf over WebSocket between the browser and the gateway, because that path is speed-critical — hundreds of NPCs updating positions every tick. JSON-RPC for lifecycle messages. REST for service discovery.

💬 **ANTICIPATED QUESTION**: *"Wait, why three protocols?"*

ANSWER: *"Because each job has different requirements. Speed-critical bulk data is protobuf-over-WebSocket. Structured lifecycle calls are JSON-RPC. Reading discovery metadata is plain REST. Production systems pick the right tool for each job; they don't force everything through one protocol."*

**Second**, the green box in the middle is the **Go Gateway**.

> 🔍 **POINT AT** the "Go Gateway" box, then specifically at "Hub" and "Switchboard"

The word "Gateway" just means a service that sits between the frontend and the backend agents and routes traffic. Written in Go because Go handles thousands of concurrent connections efficiently — implementation choice. You could write a gateway in Python, Node, Rust, anything.

Inside the Gateway, two parts. The **Hub** handles routing within one gateway instance. If you scale horizontally — three copies of the gateway for load balancing — the **Switchboard** keeps state in sync across copies.

💬 **ANTICIPATED QUESTION**: *"What's a Hub?"*

ANSWER: *"Think of a phone-company switchboard operator from the old days. The Hub knows which agent is at which address, takes incoming messages, forwards them to the right agent. Pure plumbing — pure traffic routing."*

**Third**, the arrows down to the agents.

> 🔍 **POINT AT** the "Redis Pub/Sub" arrow

From the gateway down to the Python agents, the actual transport is Redis Pub/Sub. That's how the gateway scales to hundreds of agents — it publishes events to Redis channels, and the agents subscribe to the channels they care about.

💬 **ANTICIPATED QUESTION**: *"What's pub/sub? What's fan-out? What's batching?"*

ANSWER: *"Publisher/subscriber pattern. One publisher writes a message, many subscribers receive it. **Fan-out** is one-to-many — the simulator emits 'race tick 1247: weather changed to rain' once, and 500 runners need to know. Pub/sub fans the message out to all of them. **Batching** is the opposite — instead of sending 500 individual position updates to the browser, the gateway waits 100 milliseconds, collects them all, sends one merged message. Browser doesn't die."*

---

## Slide 0.5 — A2A Network Topology diagram

🎬 **PRODUCTION**
- **W-SLIDES** — advance to slide with `assets/race-condition-a2a-topology.png`

🎙️ **NARRATION**

Zoom in on what happens for a single request. This shows the **dispatch flow** — how one message reaches one agent.

> 🔍 **POINT AT** the "Tester UI" box, follow the arrows down

You send an HTTP POST to the Gateway. The Gateway does two things in parallel:

> 🔍 **POINT AT** the "1. publish event" arrow

**Step one**: publishes an event to Redis on a channel called `simulation:orchestration`. Any agent already running and subscribed to that channel — those are the "hot" agents — picks the event up immediately. Low latency, milliseconds.

> 🔍 **POINT AT** the "2. track session" arrow

**Step two**: tracks the session in something called the **Session Registry**.

💬 **ANTICIPATED QUESTION** *(this one matters — call it out before they ask)*:

*"Wait, Session Registry — is that the Agent Registry you've been talking about?"*

ANSWER: *"No. Different thing, similar name. The **Session Registry** here is distributed state — it tracks which gateway instance is handling which session. Basically a shared key-value store. The **Agent Registry** I've been mentioning is a catalog of agents and their capabilities. We'll cover that in detail later. Just remember: when this diagram says 'Session Registry,' it has nothing to do with discovering agents."*

> 🔍 **POINT AT** the "Background Redis Dispatcher" and "ADK Runner" boxes

For cold agents — ones not currently subscribed — there's a Background Redis Dispatcher that watches for events meant for them and HTTP-pokes them awake. Once they boot, they subscribe like the hot ones.

This is called dual dispatch — pub/sub for hot agents, HTTP poke for cold ones. It's how race-condition handles scale without keeping every agent process running 24/7.

---

## Slide 0.6 — The gap (with nuance)

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the "gap" slide:
  ```
  race-condition uses Agent Registry for MCP tool discovery       ✅
  race-condition uses a per-Gateway in-memory registry for A2A    ⚠️
  race-condition does NOT use Google Cloud Agent Registry for A2A ❌
  ```

🎙️ **NARRATION**

OK, those two architecture slides showed race-condition is real and serious. Now I want you to notice something specific — carefully, because this is more nuanced than people usually present it.

**Where does race-condition use the Google Cloud Agent Registry?**

Only in one place: when an agent needs to call the Google Maps MCP server, the planner looks up Maps in the Agent Registry and gets back its URL. So the Registry holds Maps.

**Does that mean race-condition has no agent-card discovery at all?** No — and here's the nuance. Race-condition's own docs admit this directly:

> 🔍 **OPTIONAL: switch to W-EDITOR**, open `/Users/annie/Documents/Demo/race-condition/docs/speaking-outline-a2a-registry-eval.md`, scroll to the bootstrap-sequence paragraph

> *"At startup, the Go gateway reads `AGENT_URLS` (a comma-separated list of base URLs from `.env`). It hits `/.well-known/agent-card.json` on each URL, parses the card, and registers the agent's name, URL, skills, and dispatch mode into an in-memory registry. No service mesh. No external registry. Just HTTP and a well-known path."*

So race-condition **does** read agent cards. It **does** build a registry. But that registry is:

- **In-memory** — lives inside one Gateway process
- **Static** — populated from a hardcoded `AGENT_URLS` list in env config
- **Local** — only that Gateway knows about it; nothing else can query it
- **Not capability-queryable** — to add a runner, edit `AGENT_URLS` and restart

So race-condition isn't doing the *wrong* thing. It's doing a *limited* version of the right thing — local registry instead of shared, static list instead of dynamic, per-Gateway instead of org-wide.

> 🔍 **POINT AT** the ⚠️

This gap costs you something concrete. Imagine another team in your company ships a heat-adapted runner — a different runner variant. With race-condition's current approach, **the Gateway has to know its URL in advance**. Somebody updates `AGENT_URLS` in `.env`. Somebody restarts the Gateway. The new team's agent isn't discoverable by anyone else's system — only by Gateways that have its URL configured.

The agents are decoupled at *runtime* — they talk over A2A, which is great. But discovery is coupled at *configuration time*.

So the question this talk answers is: **what would change if race-condition pushed its in-memory registry up into Google Cloud Agent Registry — making it shared, dynamic, and queryable across systems?**

---

## Slide 0.7 — Today's agenda

🎬 **PRODUCTION**
- **W-SLIDES** — advance to agenda slide

🎙️ **NARRATION**

Here's the path. Five build-ups and one callback at the end.

1. ADK — what an agent looks like in code
2. A2A — the wire protocol that makes agents talk
3. The discovery problem, shown live
4. Agent Registry — capability-based discovery
5. Demo: three agents collaborating, zero hardcoded URLs
6. Tie back to race-condition

Let's go.

---

# 🎬 ACT 1 — ADK, the building block (3 min)

## Slide 1.1 — "An agent = LLM + tools + reasoning loop"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the equation slide with the code snippet

🎙️ **NARRATION**

Let's start at the bottom: what's an agent?

In ADK terms, an agent is three things glued together. A language model — say Gemini. A list of tools — Python functions the model can call. And a reasoning loop — the model picks a tool, you run it, the result feeds back into the model, the model picks the next tool. It keeps going until it has an answer.

That's it. The whole abstraction. Ten lines of code in ADK.

💬 **ANTICIPATED QUESTION**: *"What does ADK stand for?"*

ANSWER: *"Agent Development Kit. Google's open-source SDK for building agents. Cross-language — Python, Go, Java, TypeScript. 1.0 GA earlier this year. Anthropic, Microsoft, and others have similar SDKs; ADK is Google's."*

---

## Slide 1.2 — show the actual code

🎬 **PRODUCTION**
- **Switch to W-EDITOR**
- Open: `/Users/annie/Documents/Demo/agent_marketplace_demo/dog_walker_agent/agent.py`
- Scroll to line **~63** — the `root_agent = LlmAgent(...)` definition
- Have it visible to the audience

🎙️ **NARRATION**

Let me show you a real agent. This is `dog_walker_agent/agent.py` in my demo.

> 🔍 **POINT AT** the `LlmAgent(...)` call

There's the entire agent definition. Five fields. Model, name, instruction, tools, and that's it.

> 🔍 **POINT AT** the `tools=[...]` list

The tools are just Python functions — `get_dog_profile`, `get_weather`, `find_dog_parks`, `get_walking_route`. They're defined in `tools.py` next door. ADK introspects their type hints and docstrings to teach the model how to call them.

---

## Slide 1.3 — ADK Web demo (live)

🎬 **PRODUCTION**
- **Switch to W-ADKWEB** (http://localhost:8765)
- In the agent dropdown at the top, pick `dog_walker_agent`
- Click **+ New Session** (top-right)
- Type into the chat box at the bottom: `Walk Buddy this afternoon at 24th and Mission SF`
- Press Enter
- ⏱️ Wait ~30–45 seconds for the agent to complete

🎙️ **NARRATION** *(while it runs — narrate the tool events as they appear in the right panel)*

I'm running this in ADK Web — a browser UI that ships with ADK, lets you chat with an agent and see what it's doing inside.

I picked `dog_walker_agent`. New session. And I asked: *"Walk Buddy this afternoon, we live at 24th and Mission in San Francisco."*

Watch the right panel. The agent is calling tools.

> 🔍 **POINT AT** each tool event in the right panel as it appears

- First it called `get_dog_profile` — a tool that reads a local JSON file describing Buddy. He's a Lab, three years old, high energy, doesn't tolerate heat above 85 degrees.
- Then `get_weather` — a real call to the wttr.in weather service. It's 71 degrees and partly cloudy in SF right now.
- Then `find_dog_parks` — this hits the Google Maps Places API and finds real dog parks near 24th and Mission.
- And finally `get_walking_route` — Google Maps Routes API building an actual walking route.

> 🔍 **POINT AT** the final response in the main chat panel

Here's the output. A real plan. Garfield Square Park, 11 minutes walk each way, a note about bringing water because Buddy needs hydration above 70 degrees. A working Google Maps URL at the bottom.

This is what an ADK agent does — it reasons about a task, calls real tools to get real data, produces a useful answer.

But this agent only exists on my laptop. Nobody else can use it. If another team — say the trip-planning team — wanted to call my agent for "when our user is going on vacation, arrange dog walks," they have no way to do that.

That's the next problem. How do agents talk to each other?

---

# 🎬 ACT 2 — The collaboration problem (1 min)

## Slide 2.1 — "Two ways agents can talk"

🎬 **PRODUCTION**
- **Switch to W-SLIDES**

🎙️ **NARRATION**

You have two options today for agent collaboration. Both have problems.

**Option one**: in-process sub-agents. ADK supports this — stick one agent inside another as a sub-agent. Fast, easy, works great. But everything has to be in the same Python process, same deploy, owned by the same team. Doesn't scale once you have multiple teams.

**Option two**: hardcoded HTTP calls. Your orchestrator opens a URL and POSTs JSON. Decoupled processes, fine. But no standard contract. Every caller reads docs to figure out what every agent does. Add a new agent, every caller has to be updated.

The fix is exactly what HTTP did for websites — a standard wire protocol. For agents, that protocol is called **A2A**.

---

# 🎬 ACT 3 — A2A: agents talking to agents (5 min)

## Slide 3.1 — A2A overview

🎬 **PRODUCTION**
- **W-SLIDES** — advance to A2A title slide

🎙️ **NARRATION**

A2A stands for Agent-to-Agent. Open protocol. JSON-RPC 2.0 over HTTP — fancy way of saying "JSON requests with a defined shape."

Three things matter about A2A:

**First, it's framework-agnostic.** Native support in Google ADK, LangGraph, CrewAI, LlamaIndex, AutoGen, Semantic Kernel — every major agent framework. A LangGraph agent at your company can call an ADK agent at another company without either side caring what framework the other uses.

**Second, it's been donated to the Linux Foundation.** Not Google-controlled. Microsoft, AWS, Salesforce, SAP, ServiceNow, IBM all on the steering committee. 150+ orgs running A2A in production this year.

**Third — and this matters most for today** — every A2A agent serves something called an **agent card** at a well-known URL.

---

## Slide 3.2 — "The Agent Card"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the well-known URL slide

🎙️ **NARRATION**

Every A2A agent has a card. Lives at a well-known URL: slash dot-well-known slash agent-card dot json. Hit that URL and you learn everything about the agent: name, version, where to send messages, and most importantly, what skills it has.

Let me show you a real one.

---

## Slide 3.3 — curl the agent card

🎬 **PRODUCTION**
- **Switch to W-TERM2**
- Run this exact command:

```bash
curl -s http://localhost:8001/.well-known/agent-card.json | jq .
```

⏱️ JSON renders instantly. Make sure the terminal window is big enough that the audience can read it.

🎙️ **NARRATION** *(while pointing at the rendered JSON)*

I'll curl my dog walker's agent card. There it is.

> 🔍 **POINT AT** the top fields (`name`, `description`, `url`, `version`)

Name: `dog_walker_agent`. Description, version, URL, protocol version. Standard metadata.

> 🔍 **SCROLL DOWN** to the `skills` array and POINT AT it

And look at the **skills** array.

Three skills declared: `plan_walk`, `recommend_dog_park`, `check_walk_conditions`. Each has an ID, name, description, and tags — things like "dog," "walk," "route," "pet."

**This is the discovery primitive.** When another agent wants to find someone who can plan a walk, this is what it searches against. We'll come back to it.

🎬 **PRODUCTION** — OPTIONAL DEMO if race-condition is running locally (W-RACE was set up):

Switch to W-TERM2, run:

```bash
curl -s http://localhost:9105/.well-known/agent-card.json | jq .
```

🎙️ **NARRATION** *(only if you ran the optional curl)*

Same well-known path, totally different agent. This is race-condition's planner — port 9105 instead of my dog walker on 8001. The file shape is **identical**. That's the A2A agent card spec doing its job — universal across any A2A-compliant agent, regardless of framework, regardless of domain. My dog walker, race-condition's planner, a LangGraph agent at another company — all serve the same shape at the same path.

💬 **ANTICIPATED QUESTION**: *"Is 'skill' here the same as the 'agent skills' I've heard about in ADK or Claude Code?"*

ANSWER: *"No, and this is a confusing terminology collision."*

*"**A2A AgentSkill** — what you're looking at right now — is **metadata**. A declaration. It says 'I can do X.' No code. Just a label."*

*"**ADK Skill** (and Claude Code Skill — they're similar) is a **package**. A folder with a `SKILL.md` file plus tools and examples. You load it at runtime to give your agent a new capability."*

*"Same word, different concept. A2A skill = a yellow-pages entry. ADK skill = an installable booklet of know-how. They can coexist for the same agent — ADK skill teaches the agent how to do the work, A2A skill advertises that it can."*

---

## Slide 3.4 — How an ADK agent becomes A2A

🎬 **PRODUCTION**
- **Switch to W-EDITOR**
- Open: `/Users/annie/Documents/Demo/agent_marketplace_demo/dog_walker_agent/server.py`
- Highlight the `to_a2a(...)` call

🎙️ **NARRATION**

How do you turn an ADK agent into an A2A server? In ADK, literally one function call. Here it is in my server file.

> 🔍 **POINT AT** the `to_a2a(...)` call

`to_a2a` takes the agent and an agent card, returns a Starlette app. You run it with uvicorn — there's your A2A server. Framework handles all the JSON-RPC protocol details.

One line transformation. Local agent → network-callable A2A agent.

---

## Slide 3.5 — A2A Inspector demo

🎬 **PRODUCTION**
- **Switch to W-INSPECTOR** (https://a2ainspect.com/ or your local Docker copy)
- In the URL input at the top, type: `http://localhost:8001`
- Click **Connect**
- ⏱️ Wait for the agent card to load (1-2 sec)
- Click the **Agent Card** tab — show the rendered JSON
- Click the **Chat** tab
- Type into the chat box: `Walk Buddy this afternoon at 24th and Mission SF`
- Press Send
- **While the agent runs**, click the **Console** tab — show the raw JSON-RPC traffic

⏱️ The agent takes ~30 sec. Console tab updates in real time.

🎙️ **NARRATION**

Now let me prove A2A is a real protocol, not just an ADK convention. I'll use a tool called **A2A Inspector**. Community-built, runs in your browser, connects to any A2A agent.

I enter my dog walker's URL. Connect. The agent card loads — same JSON I just curled, rendered nicely.

> 🔍 **POINT AT** the Chat tab

Switch to Chat. Same prompt: *"Walk Buddy this afternoon at 24th and Mission SF."*

> 🔍 **CLICK** the Console tab while the agent reasons

Watch the Console tab. That's raw JSON-RPC traffic — actual bytes going over the wire between Inspector and my agent. **This is A2A.**

The point: A2A Inspector isn't from Google. Not from ADK. Just speaks A2A. Any client, any framework, anywhere — if it speaks A2A, it talks to my agent. That's the value of an open protocol.

---

## Slide 3.6 — "What we have so far"

🎬 **PRODUCTION**
- **Switch back to W-SLIDES**

🎙️ **NARRATION**

OK. We can build agents with ADK. Expose them over a standard protocol with A2A. They self-describe their capabilities through agent cards.

But there's still one gap. **Whoever wants to call our agent needs to know its URL.** That's where most A2A tutorials stop — they show you `to_a2a`, they hardcode a URL, you're done.

Hardcoded URLs don't scale. So how does anyone *find* our agent? That's the next problem.

---

# 🎬 ACT 4 — The discovery problem: show the pain (3 min)

## Slide 4.1 — The setup

🎬 **PRODUCTION**
- **W-SLIDES** — title slide for Act 4

🎙️ **NARRATION**

Here's the question. We have A2A. Any agent can call any other agent over a standard protocol. But how does the orchestrator — the agent that routes user requests — even know that the trip planner and the dog walker exist?

I'm not going to show you a hypothetical code snippet. I built two versions of the orchestrator in this demo — one with Registry, one without. Let me run the **without** version live so you can feel the pain.

---

## Slide 4.2 — The no-Registry orchestrator (code)

🎬 **PRODUCTION**
- **Switch to W-EDITOR**
- Open: `/Users/annie/Documents/Demo/agent_marketplace_demo/orchestrator_agent/agent_without_registry.py`
- Scroll to the `KNOWN_AGENTS` dict (around line 50)

🎙️ **NARRATION**

> 🔍 **POINT AT** the `KNOWN_AGENTS` dict

This is the whole orchestrator-without-Registry approach in one variable. A Python dict mapping agent name to URL. Two entries today.

> 🔍 **POINT AT** the comments below the dict ("When the flight-booking team ships..." etc.)

The comments tell you what happens when the company grows. Flight booking team ships an agent? Add an entry. Redeploy. Support team? Add an entry. Redeploy. Every new agent in the company = one more entry here = one more redeploy.

💬 **ANTICIPATED QUESTION**: *"Why don't they just deploy to Cloud Run and use Cloud Run URLs? Those are stable."*

ANSWER: *"Sharp question. Cloud Run URLs are stable. The real pain isn't URL stability."*

*"The pain is **the mapping** — which URL provides which capability. Cloud Run gives you a stable URL. It doesn't give you a directory that says 'this URL plans trips, that URL walks dogs.' You still maintain that mapping in your orchestrator code."*

---

## Slide 4.3 — LIVE DEMO: two queries, same orchestrator

🎬 **PRODUCTION**
- **Switch to W-TERM2**
- (Confirm you're in the project dir: `pwd` should show `/Users/annie/Documents/Demo/agent_marketplace_demo`)

**Demo 1 — query that's IN the dict (should succeed)**

```bash
uv run python orchestrator_agent/agent_without_registry.py \
  "Walk Buddy this afternoon at 24th and Mission SF"
```

⏱️ Wait ~30 sec. You should see one tool call (`call_a2a_agent("dog_walker", ...)`) and a real walk plan.

🎙️ **NARRATION** *(during Demo 1)*

I'll run two queries against the same orchestrator binary. Same code, same model. Watch what happens.

First query: *"Walk Buddy this afternoon at 24th and Mission SF."*

> 🔍 **POINT AT** the tool call in the trace

One tool call. `call_a2a_agent("dog_walker", ...)`. Real plan comes back — Precita Park, 30-minute loop, weather note. Works perfectly. Because `dog_walker` is in the dict.

🎬 **PRODUCTION** — **Demo 2** — query that's NOT in the dict (should fail)

```bash
uv run python orchestrator_agent/agent_without_registry.py \
  "Book me a flight to Tokyo for next week"
```

⏱️ This comes back almost instantly — the orchestrator gives up without making any tool calls.

🎙️ **NARRATION** *(during Demo 2)*

Same orchestrator. New query: *"Book me a flight to Tokyo for next week."*

> 🔍 **POINT AT** the "FINAL RESPONSE" output

**Zero tool calls.** The LLM read its hardcoded instruction, saw that no flight agent is in `KNOWN_AGENTS`, gave up immediately:

*"I don't have an agent registered for that. With Agent Registry, I could have searched by capability — but in this version I only know about trip_planner and dog_walker."*

That's the failure mode. Same orchestrator. Just because flight booking isn't hardcoded, the system is dead in the water.

---

## Slide 4.4 — "What breaks"

🎬 **PRODUCTION**
- **Switch to W-SLIDES** — advance to the "what breaks" four-bullet slide

🎙️ **NARRATION**

You just saw the fourth bullet live. Let me name the other three.

**One**: every time a new agent ships in your company, somebody has to add it to this file and redeploy the orchestrator. The orchestrator becomes a directory of every agent in the org.

**Two**: dev, staging, production environments. Three sets of URLs to keep in sync. Cloud Run URLs are stable, but the mapping of capability to URL lives in this file.

**Three**: two teams ship similar agents. Maybe Team A's trip planner is better for sprints, Team B's is better for family trips. Orchestrator has to encode that logic.

**Four** — the one we just saw: another team built the perfect agent. You don't know it exists. No catalog to discover from.

---

## Slide 4.5 — "What we actually want"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the 2-line code snippet slide

🎙️ **NARRATION**

This is what we actually want. Two lines.

The orchestrator doesn't know agent names. Doesn't know URLs. Doesn't know who's out there. It asks: **"who can plan a trip?"** The catalog answers.

And here's the magic part — **the moment somebody at another team registers a flight-booking agent in the catalog**, my same orchestrator binary, with no code changes, succeeds when I ask it to book a flight. Discovery is dynamic.

---

## Slide 4.6 — 💡 The "aha"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the aha slide

🎙️ **NARRATION** *(slow down here — this is the punchline of the whole talk)*

The shift I want you to take away: **hardcoded routing to capability-based routing.** From the orchestrator owning a config of every agent in the world, to the orchestrator asking the world a question.

When you flip that switch:

- **New agents become discoverable the moment they register.** No code change.
- **Old agents disappear gracefully.** Entries leave the catalog; queries stop finding them.
- **Multiple matches just work.** Registry returns all; caller picks.

That's the Registry promise. Let me show you what it actually is.

---

# 🎬 ACT 5 — Agent Registry: the catalog (5 min)

## Slide 5.1 — "Agent Registry"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to Registry intro slide

🎙️ **NARRATION**

Critical thing to get out of the way first: **the Agent Registry is a catalog, not a runtime.**

A catalog is a directory of pointers. "Agent X lives at URL Y with these skills." It does NOT run the agent. It does NOT host the agent. The agent could be on Cloud Run, on Vertex AI Agent Engine, on a Kubernetes cluster, on your laptop, in someone's garage. The Registry doesn't care. It just stores the address.

This is the misconception that trips people up most: "agents only appear in the Registry if I deploy to Agent Engine." Wrong. Agent Engine deploy is **one way**. Manual registration pointing at any URL — including localhost — is another way.

---

## Slide 5.2 — Two ways to register

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the table comparing manual vs auto

🎙️ **NARRATION**

Manual via `gcloud agent-registry services create`, or auto when you deploy to Vertex AI Agent Engine.

In this demo, I use the manual path because it lets me run everything on my laptop without a deploy. My `register.py` reads my agent's card, calls gcloud with the localhost URL. Registry stores it. Done.

---

## Slide 5.3 — Demo: Agent Registry console

🎬 **PRODUCTION**
- **Switch to W-CONSOLE** (https://console.cloud.google.com/agent-platform/agent-registry?project=neon-emitter-458622-e3)
- The Agents tab should already be selected. Show the list.
- Click the row for `dog_walker_agent`
- ⏱️ The detail panel loads (~2 sec)

🎙️ **NARRATION**

This is the Agent Registry in Google Cloud Console.

> 🔍 **POINT AT** the row list

My two agents are here — `dog_walker_agent` and `trip_planner_agent`. Both auto-discovered, both visible to any other agent in this project.

Let me click into the dog walker.

> 🔍 **POINT AT** the "Interface URL" field

**Look at the URL.** Literally `http://localhost:8001/`. The Registry doesn't care that this isn't reachable from anywhere except my laptop. I told it that URL; it stored it.

> 🔍 **SCROLL DOWN** to the skills section

And the three skills got auto-indexed when the Registry scraped the agent card. `plan_walk`, `recommend_dog_park`, `check_walk_conditions`. Each with descriptions and tags. The Registry knows what this agent can do, well enough for other agents to search by capability.

---

## Slide 5.4 — 💡 Skills = yellow pages, not phone book

🎬 **PRODUCTION**
- **Switch to W-SLIDES**

🎙️ **NARRATION**

For anyone who grew up after phone books, quick analogy.

Phone book: alphabetical list by name. Look up "Alice Smith" by flipping to S.

Yellow pages: same data, organized by category. "Plumbers near you." "Lawyers near you." Didn't need to know the plumber's name — just needed to know you needed a plumber.

Registry without skills = phone book. You'd need to know each agent's name.

Registry **with skills** = yellow pages. You describe what you need, you get back the agents that match.

💬 **ANTICIPATED QUESTION**: *"How does the Registry actually find a matching skill?"*

ANSWER: *"Mostly keyword and semantic matching against the skill's description and tags. When you search for 'plan a trip,' the Registry matches against the trip planner's `plan_trip` skill description, which mentions 'plan a short city trip,' and against tags like 'trip,' 'travel,' 'planning.' Multiple matches get returned ranked; the caller picks."*

---

## Slide 5.5 — MCP (the other half)

🎬 **PRODUCTION**
- **W-SLIDES** — advance to MCP comparison slide

🎙️ **NARRATION**

Quick aside on MCP — Model Context Protocol. Anthropic introduced it in 2024. Standard for an agent calling tools — functions, data sources, APIs.

A2A, by contrast, is for an agent calling other agents. Both open protocols. Different problems, different layers.

💬 **ANTICIPATED QUESTION**: *"So tools and skills are basically the same thing?"*

ANSWER: *"Same idea, different scope. A **tool** in MCP is one function call. A **skill** in A2A is usually a higher-level capability that may use many tools internally."*

*"For example, the dog walker has a skill called `plan_walk`. That single skill uses four MCP-style tools internally: `get_dog_profile`, `get_weather`, `find_dog_parks`, `get_walking_route`. The skill is the outer capability; tools are the inner functions."*

*"For discovery purposes, the Registry treats both as searchable metadata."*

---

## Slide 5.6 — "Where MCP shows up in this demo"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the honest two-row table

🎙️ **NARRATION**

Honesty moment. Two places MCP shows up, but I only use one.

**Used**: the Agent Registry is itself an MCP server. When my orchestrator searches for agents, it's calling MCP tools — `search_agents`, `list_agents`, `get_agent` — against `agentregistry.googleapis.com/mcp`. So I AM using MCP — for discovery.

**Not used**: I could have called Google Maps via the Maps MCP server, which IS in the Registry. But I cheated and called Maps' REST API directly because less moving parts. In a pure version, the agent would discover Maps MCP via the Registry, then call its tools — and you could swap Google Maps for OpenStreetMap MCP by updating a single Registry entry, no code changes.

The principle stands: MCP and A2A coexist. Registry holds both. **In your Google Cloud project, more than 20 first-party Google MCP servers — BigQuery, Cloud Storage, Compute, Spanner, Pub/Sub, Maps — are already in the Registry waiting for you.** Nobody had to register them; enabled APIs put them there.

---

## Slide 5.7 — The connection

🎬 **PRODUCTION**
- **W-SLIDES** — advance to the flow diagram (Agent A → Registry → Trip Planner)

🎙️ **NARRATION**

This is the flow.

Agent A needs help. Asks the Registry: "who can plan a trip?" Registry returns matching agents — names, URLs, skills.

Agent A picks one — usually the top match — and makes an A2A call to that URL. Trip planner does its work, responds.

**Zero hardcoded URLs anywhere in Agent A's code.** That's the win.

---

# 🎬 ACT 6 — The climax: peer-to-peer in action (5 min)

## Slide 6.1 — "Three agents collaborating"

🎬 **PRODUCTION**
- **W-SLIDES** — title slide

🎙️ **NARRATION**

Last act before we tie it all together. I have three agents. An Orchestrator. Two specialists — Trip Planner and Dog Walker.

None of them have any other agent's URL in their code. They only know how to query the Registry.

I'm going to give the Orchestrator a request that needs **both** specialists. Watch what happens.

---

## Slide 6.2 — The live demo

🎬 **PRODUCTION**
- **Switch to W-ADKWEB** (http://localhost:8765)
- In the agent dropdown, pick `orchestrator_agent`
- Click **+ New Session**
- Type into the chat box: `Going to Kyoto for 5 days, what about Buddy while I am away`
- Press Enter
- ⏱️ This takes ~90 sec to 2 minutes total — narrate as events appear

🎙️ **NARRATION** *(narrate each tool event as it appears in the right panel — slow down here)*

I'll pick the orchestrator. New session. Ask:

*"Going to Kyoto for 5 days, what about Buddy while I am away?"*

This will take about 90 seconds to a couple of minutes — lots of reasoning happening. Let me narrate.

> 🔍 **POINT AT** event #1 (registry_search_agents)

**Event 1.** The orchestrator called `registry_search_agents` with the query "trip planning." That's an MCP tool call against the Registry MCP server. Asking, "who can plan a trip?"

> 🔍 **POINT AT** event #2 (result)

**Event 2.** Registry came back with the trip planner. Orchestrator now has a resource name for it.

> 🔍 **POINT AT** event #3 (call_remote_a2a_agent)

**Event 3.** Orchestrator just sent the user's exact message — verbatim, including "what about Buddy" — over A2A to the trip planner.

**(While the trip planner runs internally, fill the time.)**

Trip planner is reasoning now. Calling Google Maps to find Kyoto attractions. Fushimi Inari, Kiyomizu-dera, Kinkaku-ji — grouping them geographically by day.

**But here's the moment.** The trip planner sees "Buddy" in the message. And — *it does the same Registry search the orchestrator just did*. Calls `registry_search_agents` with the query "dog."

> 🔍 **POINT AT** the peer-search event when it appears

**There.** Trip planner just found the dog walker via the Registry. Now trip planner is calling dog walker over A2A. **Agent calling agent.**

**(Wait for the final response.)**

> 🔍 **POINT AT** the final response in the main chat panel

**Final response.** Two sections. Five-day Kyoto itinerary with real temples and walking distances. And a "Pet care for Buddy" section — daily routine, morning walk, afternoon walk, real SF parks, logistics for a multi-day absence.

---

## Slide 6.3 — "What just happened"

🎬 **PRODUCTION**
- **Switch to W-SLIDES** — advance to the flow diagram

🎙️ **NARRATION**

Three agents collaborated. Three Registry lookups. Two A2A delegations.

Most importantly: **none of them had any of the others' URLs in their code.** If I added a flight-booking agent tomorrow and registered it, the orchestrator would discover and route to it the moment someone asked about flights.

---

# 🎬 ACT 7 — What this unlocks + race-condition callback (4 min)

## Slide 7.1 — "Why this matters"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to three-bullet slide

🎙️ **NARRATION**

Three things this unlocks.

**One. Different teams own different agents.** Trip-planning team and dog-walking team don't need to know each other exist. Each publishes to the same Registry. Consumers find them by skill.

**Two. Replace, scale, redeploy without breaking callers.** Ship dog walker v2 — it enters the Registry. Take v1 out — it leaves. Callers don't change a line. They were always searching by skill.

**Three. Cross-framework interop.** This demo is all ADK. But the same Registry could hold LangGraph agents, CrewAI agents, custom A2A servers. Protocol is open. Catalog is uniform.

---

## Slide 7.2 — "Without each piece"

🎬 **PRODUCTION**
- **W-SLIDES** — advance to four-row table

🎙️ **NARRATION**

Let me recap what each piece gives you by imagining its absence.

**Without A2A:** every pair of agents has bespoke integration. Framework lock-in. With A2A: one wire protocol, any framework calls any framework.

**Without Agent Registry:** hardcoded URLs, `if/elif` routing. With Registry: capability-based discovery, new agents auto-found.

**Without Skills:** Registry is a phone book — must know names. With Skills: yellow pages — say what you need.

**Without MCP:** custom code for every tool. With MCP: standard tool protocol, swappable, discoverable.

Take any piece out, the system regresses. Together — composable agent ecosystem. None of these are nice-to-haves; each fixes a specific failure.

---

## Slide 7.3 — 🔁 Callback: apply this to race-condition

🎬 **PRODUCTION**
- **W-SLIDES** — advance to before/after diagrams comparing race-condition's gateway

🎙️ **NARRATION**

Remember race-condition from the opening?

Today, its Gateway reads `AGENT_URLS` from `.env` at startup and builds an in-memory registry of agent cards. Per-instance, static, not queryable across systems. To add a runner variant, somebody updates `AGENT_URLS` and restarts.

**What if that didn't have to happen?**

Apply the pattern we just demoed. The Gateway stops reading from `.env` and starts asking the Google Cloud Agent Registry: "who can run a marathon?" Any team in the company ships a runner variant — heat-adapted, sprint-finish, dietary-strategy — and the Gateway picks it up the moment it's registered. **No Gateway code changes. No `.env` edits.**

That's the lever. We demoed it at toy scale with three small agents. Race-condition is the production-scale chassis it could run on top of.

---

# 🎬 ACT 8 — Closing (1+ min)

## Slide 8.1 — One sentence

🎬 **PRODUCTION**
- **W-SLIDES** — advance to closing quote slide

🎙️ **NARRATION**

If you take away one sentence from today:

> *"The Agent Registry lets agents find each other by capability, so I can replace, redeploy, or add agents without touching anyone else's code."*

That's the difference between a wiring project and an ecosystem.

---

## Slide 8.2 — Where to start

🎬 **PRODUCTION**
- **W-SLIDES** — final slide with links

🎙️ **NARRATION**

- ADK docs — adk.dev
- A2A spec — a2a-protocol.org
- This demo — github.com/cuppibla/agent_marketplace_demo
- race-condition — github.com/GoogleCloudPlatform/race-condition

**Thanks. Questions?**

---

# Q&A — likely questions and crisp answers

| Q | Concise answer |
|---|---|
| MCP vs A2A really? | MCP = call a tool (function). A2A = talk to an agent (colleague with reasoning). |
| Why not sub-agents in ADK? | Tightly coupled. A2A is for cross-team, cross-deploy, cross-framework. |
| Can LangGraph call my ADK agent? | Yes — point of A2A. |
| How do agents authenticate? | OAuth bearer, API keys, service accounts. Card declares supported schemes. |
| Why don't Cloud Run URLs solve this? | URLs are stable. Mapping of capability → URL still lives in your code. |
| How does Registry know my skills? | Scrapes agent card at `/.well-known/agent-card.json`. Auto-indexed. |
| Session Registry = Agent Registry? | NO. Session Registry = distributed state. Agent Registry = catalog. |
| Two agents with same skill? | Registry returns all matches. Caller picks. |
| Apply to race-condition? | Replace AGENT_URLS-based bootstrap with `registry_search_agents("runner")`. Any team's runner variant becomes discoverable on registration. |
| Outside Google Cloud? | A2A + MCP are open. Other clouds will ship their own catalogs over time. |
| Cost? | Registry storage is free. You pay for compute (Vertex AI, Agent Engine, Cloud Run). |
| How to deploy for real? | `adk deploy agent-engine` packages + deploys + auto-registers. See `deploy/agent_engine.md`. |
| A2A skill = Claude skill = ADK skill? | NO. A2A skill = metadata label. ADK/Claude skill = installable package. |

---

# 🚨 If the live demo fails

Have these ready:

1. **Screenshots** of a successful peer-to-peer run (the orchestrator trace + final response)
2. **Pre-recorded screen capture** of the full peer-to-peer chain
3. **Fallback narrative**: *"The live API is having a moment — here's what should have happened…"* Walk through the screenshots.

Common failures + recovery:

- **Network slow → timeout**: switch to recording.
- **Maps API quota exceeded**: same — switch to recording.
- **Wrong session in ADK Web**: click **+ New Session** to reset.
- **Server died**: open W-TERM1, `./deploy/start_local.sh`, wait 10s, retry.
- **Race-condition not up for optional curl**: skip that beat, the dog walker curl is enough.

---

# 📋 One-page cheat sheet (print or have on a second screen)

```
PRE-SHOW (5 min before)
  W-TERM1: ./deploy/start_local.sh
  W-TERM1: uv run adk web . --port 8765
  W-TERM2: curl checks (DogWalker 8001, TripPlanner 8002, ADK Web 8765)
  Open W-ADKWEB, W-INSPECTOR, W-CONSOLE tabs
  W-EDITOR: open dog_walker_agent/agent.py, agent_card.py,
            orchestrator_agent/agent.py, agent_without_registry.py
  OPTIONAL: cd race-condition && make dev    (if you want optional Act 3 curl)

ACT 0 (7 min) — RACE-CONDITION SHOWS THE GAP
  W-SLIDES: "Built an agent. Now what?" — hands-up question
  W-SLIDES: race-condition banner
  Visual: cached replay / video clip / screenshot
  W-SLIDES: Hybrid Transport Model diagram — explain Hub, Switchboard, Pub/Sub
            ANSWER inline: 3 protocols, fan-out, batching, pub/sub
  W-SLIDES: A2A Network Topology diagram — explain dual dispatch
            ANSWER inline: Session Registry ≠ Agent Registry
  W-SLIDES: 🎯 Gap slide (3 lines: ✅ MCP, ⚠️ in-memory, ❌ no GCP Registry for A2A)
            Quote race-condition docs about AGENT_URLS
  W-SLIDES: agenda (5 builds + 1 callback)

ACT 1 (3 min) — ADK
  W-EDITOR: dog_walker_agent/agent.py at LlmAgent definition
  W-ADKWEB: pick dog_walker_agent, New Session
  TYPE: "Walk Buddy this afternoon at 24th and Mission SF"
  Narrate 4 tool events live
  Final plan with map URL

ACT 2 (1 min) — collab problem
  W-SLIDES: in-process vs hardcoded HTTP — both have problems
  SAY: "We need a standard wire protocol — A2A."

ACT 3 (5 min) — A2A
  W-SLIDES: A2A 3 bullets
  W-SLIDES: well-known path
  W-TERM2: curl http://localhost:8001/.well-known/agent-card.json | jq .
  POINT AT: skills array
  CLARIFY: A2A skill (metadata) vs ADK/Claude skill (package)
  OPTIONAL W-TERM2: curl http://localhost:9105/.well-known/agent-card.json | jq .
    (only if race-condition running)
  W-EDITOR: dog_walker_agent/server.py at to_a2a() call
  W-INSPECTOR: connect to http://localhost:8001
    Agent Card tab → Chat tab → send same message → Console tab during run
  W-SLIDES: "what we have so far"

ACT 4 (3 min) — SHOW THE PAIN (LIVE DEMO)
  W-EDITOR: orchestrator_agent/agent_without_registry.py at KNOWN_AGENTS dict
  CLARIFY: Cloud Run URLs don't solve this — mapping is the pain
  W-TERM2 Demo 1: uv run python orchestrator_agent/agent_without_registry.py \
                    "Walk Buddy this afternoon at 24th and Mission SF"
    → 1 tool call, real plan (dog_walker in dict)
  W-TERM2 Demo 2: uv run python orchestrator_agent/agent_without_registry.py \
                    "Book me a flight to Tokyo for next week"
    → 0 tool calls, gives up (flight agent NOT in dict)
  W-SLIDES: 4 ways it breaks
  W-SLIDES: with Registry — 2 lines
  SAY: "moment someone registers a flight agent, the SAME Registry orchestrator
        starts succeeding. Discovery is dynamic."
  W-SLIDES: 💡 aha — hardcoded → capability-based

ACT 5 (5 min) — Registry
  W-SLIDES: catalog vs runtime
  W-SLIDES: two ways to register
  W-CONSOLE: click dog_walker_agent → show skills, URL=localhost (reaction)
  W-SLIDES: 💡 yellow pages vs phone book
  W-SLIDES: MCP vs A2A — tools vs skills
  W-SLIDES: honest note — Maps in this demo = direct API
            "22 Google MCP servers already in your Registry"
  W-SLIDES: flow diagram

ACT 6 (5 min) — CLIMAX
  W-ADKWEB: pick orchestrator_agent, New Session
  TYPE: "Going to Kyoto for 5 days, what about Buddy while I am away"
  Narrate 6 tool events live:
    1. orchestrator → registry_search_agents("trip planning")
    2. found TripPlanner
    3. orchestrator → call_remote_a2a_agent (verbatim message)
    4. TripPlanner reasons, sees "Buddy"
    5. TripPlanner → registry_search_agents("dog") → found DogWalker
    6. TripPlanner → call_remote_a2a_agent(DogWalker, ...)
    7. Combined response: itinerary + pet care

ACT 7 (4 min) — what this unlocks + race-condition callback
  W-SLIDES: 3 things (team independence, hot-swap, cross-framework)
  W-SLIDES: "without each piece" 4-row table
  W-SLIDES: 🔁 race-condition before/after
  SAY: "Gateway today: AGENT_URLS in .env, in-memory registry, restart on change.
        Gateway with this pattern: Registry.search_agents('runner').
        Any team's variant discoverable on registration."

ACT 8 (1+ min) — Closing
  W-SLIDES: one sentence
  W-SLIDES: links
  → Q&A
```
