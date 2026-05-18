# Integrating with `race-condition`

A guide for using **both** demos together to teach A2A and Agent Registry — `agent_marketplace_demo` (this repo) and [`race-condition`](../race-condition/) (Google's open-source Cloud Next '26 keynote demo).

---

## TL;DR — why they're complementary

| | `race-condition` | `agent_marketplace_demo` (this repo) |
|---|---|---|
| **Scale** | Production: hundreds of agents, Go Hub gateway, Cloud Run + Agent Engine deploy | Toy: 3 agents, all local |
| **A2A** | ✅ Heavy — planner / simulator / runner all expose A2A | ✅ Foundational — 2 A2A agents + orchestrator |
| **Agent Registry — for MCP tools** | ✅ Discovers the Maps MCP server via Registry | ❌ Calls Maps directly (would be a port to add) |
| **Agent Registry — for A2A agents** | ❌ Agents wired via the Go Hub with known URLs | ✅ Capability-based discovery via `registry_search_agents` |
| **Skills** | ✅ Declared, used as A2A capability metadata | ✅ Declared AND used as the discovery primitive |
| **Best for showing** | A2A multi-agent at scale, real production architecture | The discovery / governance layer that turns A2A from "hardcoded calls" into "yellow pages" |

**Race-condition is the perfect "before" demo for this repo's Registry story.** It shows what A2A looks like in production *without* capability-based discovery. The Hub knows every agent's URL. Add a new agent type and the Hub needs to know.

`agent_marketplace_demo` shows the next evolution: replace the "Hub knows everyone" pattern with `registry.search_agents("plan a route")`.

---

## How to weave them together in a talk

### Option A: race-condition as the "before" (recommended)

**Pacing:** ~5 min on race-condition, ~20 min on agent_marketplace_demo.

1. **Open with race-condition** (5 min):
   - Show the marathon visual (banner image, replay video, or live local demo)
   - Highlight: "Cloud Next '26 keynote, hundreds of agents, all talking A2A"
   - Point at the architecture: "Planner builds the course. Simulator drives the environment. Runners each decide their own pacing. All over A2A through a Go Hub gateway."
   - Land the gap: *"This is what A2A looks like at scale. But notice — the Hub knows where every agent lives. The Registry in this project is used for one thing: discovering the Maps MCP tool. The agents themselves are wired by URL. Add a new team's runner agent type and the Hub needs to know about it. That's the discovery problem."*

2. **Pivot to this repo** (20 min):
   - "Let me show you what changes when you push capability-based discovery one level up — to A2A agents themselves."
   - Run [PRESENTATION.md](./PRESENTATION.md) Acts 1–7 as designed.

3. **Closing tie-back**:
   - *"Race-condition shows A2A working at production scale. This demo shows how the Registry pattern they use for Maps MCP could extend to the agents themselves. Imagine the Hub didn't hardcode runner URLs — it asked the Registry 'who can run a marathon?' and dispatched to whoever's registered. That's where this is going."*

### Option B: this repo as the warm-up, race-condition as the payoff

**Pacing:** ~20 min on agent_marketplace_demo, ~5 min on race-condition.

1. Build up the A2A + Registry story with this repo (Acts 1–6 of PRESENTATION.md).
2. End with race-condition as the "now at scale" moment:
   - "Here's the same primitives at production scale. ADK agents, A2A protocol, Vertex AI Agent Engine deploy. Plus a Go gateway for high-throughput routing."
   - "Notice: race-condition uses the Registry for MCP tool discovery (Maps) but routes A2A traffic through a Hub. The Hub pattern is great for performance — batching, fan-out, controlled load. The Registry pattern is great for governance — capability-based discovery, swappable agents, multi-team."
   - "In production you'll likely want both: Registry for discovery, Hub-like gateway for high-volume routing."

### Option C: side-by-side comparison

**Pacing:** ~12 min each, with a deliberate compare/contrast.

Use a single slide with two columns the whole time:

| race-condition (production scale) | agent_marketplace_demo (discovery pattern) |
|---|---|
| 3D Angular frontend, Three.js visuals | CLI + ADK Web |
| Hundreds of NPC runner agents | 3 agents total |
| Go Hub for WebSocket fan-out | Direct A2A calls |
| Agents wired by URL through Hub | Agents found via `registry_search_agents("...")` |
| Registry used for: Maps MCP | Registry used for: A2A agents + MCP |
| Cached replay for offline demos | Live every time |

Switch back and forth — *"this is what at-scale looks like; this is what the discovery layer looks like."*

---

## Optional: live integration

If you want a "wow" moment, you can actually register race-condition's agents in **your** Agent Registry and have this repo's orchestrator discover them.

### What this would prove

> *"Race-condition and agent_marketplace_demo are different projects, owned by different teams, sharing nothing — yet because they both speak A2A and both register in the Registry, this orchestrator can call race-condition's planner without knowing anything about its codebase."*

That's the real-world A2A + Registry payoff.

### Concrete steps (sketch)

1. **Get race-condition running locally** — follow its [Getting Started skill](../race-condition/.claude/skills/getting-started/SKILL.md). It needs Docker Compose, Redis, PostgreSQL.
2. **Find the planner's A2A endpoint**. Race-condition deploys agents via `create_a2a_deployment` (see `agents/utils/deployment.py`). Locally, the planner will be reachable at a known port.
3. **Register it in your Registry**, similar to this repo's [`register.py`](./dog_walker_agent/register.py):
   ```bash
   curl -s http://localhost:<planner-port>/.well-known/agent-card.json > /tmp/planner_card.json
   gcloud alpha agent-registry services create marathon-planner \
     --location=global --project=$GOOGLE_CLOUD_PROJECT \
     --display-name="Marathon Planner (race-condition)" \
     --agent-spec-type=a2a-agent-card \
     --agent-spec-content=/tmp/planner_card.json
   ```
4. **Run this repo's orchestrator** with a marathon-flavored query:
   ```bash
   uv run python orchestrator_agent/agent.py "Plan a 10K running route through downtown Las Vegas with low elevation gain"
   ```
   The orchestrator will:
   - Search the Registry for "route planning"
   - Find race-condition's planner (alongside our TripPlanner)
   - Pick whichever is the better skill match
   - Delegate over A2A

5. **The narrative moment**: show the audience that an orchestrator written for trip planning + dog walking can route to a marathon planner from a completely separate project, with no code change — just because both registered in the same catalog.

### Caveats

- **A2A protocol versions must match.** Race-condition is on `google-adk` 1.31; this demo is on 1.33. The A2A wire format is stable but agent card schemas evolve — check `protocol_version` in both cards.
- **Auth.** Race-condition's planner may require its own auth headers if deployed to Agent Engine. Locally over Docker Compose it's typically open.
- **Skill naming.** The orchestrator picks by skill description matching, so race-condition's `create_simulation_plan` skill might not auto-match a generic "trip" query. You may need to issue a query that mentions "route" or "course."
- **Performance.** Race-condition's planner is heavier (GIS + financial modeling) — expect 30–90 sec per call.

---

## Recommended for your context

**If you're presenting in 1 talk**: use **Option A** (race-condition as the "before"). 5 min of context-setting, then the full agent_marketplace_demo arc. That's the most pedagogically clean.

**If you're presenting to a Cloud-Next audience that knows race-condition already**: use **Option B** (this repo first, race-condition as the production-scale payoff). They'll recognize the keynote demo and appreciate seeing it framed as "the same primitives, at scale."

**If you have time for a deeper workshop**: do **Option C** (side-by-side) — gives developers the full picture of when to use the Hub pattern vs the Registry pattern in their own architectures.

The **live integration** is fun but high-risk for a live talk. I'd prep it as a backup demo or a follow-up post, not the main act.

---

## Cross-references

- This repo's [PRESENTATION.md](./PRESENTATION.md) — the 25-min talk flow
- This repo's [DEMO.md](./DEMO.md) — how to demo each piece live
- Race-condition [README](../race-condition/README.md) — what it is, how to run it
- Race-condition [getting-started skill](../race-condition/.claude/skills/getting-started/SKILL.md) — fastest path to running it locally
