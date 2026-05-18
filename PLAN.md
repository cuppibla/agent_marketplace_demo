# Plan: `agent_marketplace_demo`

A runnable demo + developer tutorial showing **A2A + Agent Registry + MCP** working together. Four agents collaborate to plan trips and walk a dog, all discoverable through the Google Cloud Agent Registry.

---

## Goal

Teach developers A2A + Agent Registry by showing four agents collaborating:
- An MCP-discovery agent (existing, adapted from `discovery_agent_demo`)
- Two A2A specialists (`DogWalkerAgent`, `TripPlannerAgent`)
- An orchestrator that routes requests via Registry skill search

The demo doubles as a 4-part tutorial so devs can run each stage incrementally.

---

## Final architecture

```
User
 │ "Walk Buddy" / "Plan Kyoto trip" / "Going to Kyoto, what about Buddy?"
 ▼
OrchestratorAgent  ──► Registry.search_agents(skill)
       │                       │
       │                       ▼
       │              ┌────────────────┐
       └────────────► │ Agent Registry │ ◄─────┐
                      └────────────────┘       │
                       ▲       ▲       ▲       │ auto-register
                       │       │       │       │ on deploy
                       │       │       │       │
            ┌──────────┴──┐ ┌──┴────┐ ┌┴──────────┐
            │ DiscoveryAgt│ │DogWalk│ │TripPlanner│
            │  (existing) │ │ (A2A) │ │   (A2A)   │
            └─────────────┘ └───┬───┘ └─────┬─────┘
                                │           │
                                │ peer-to-peer (encore)
                                │ ◄─────────┘
                                ▼
                      Google Maps MCP (also in Registry)
                                ▼
                          wttr.in (weather)
```

---

## Confirmed decisions

| # | Decision | Value |
|---|---|---|
| 1 | Umbrella folder | `agent_marketplace_demo` |
| 2 | Demo city | San Francisco |
| 3 | Local-only first | Yes — deploy is Phase 7, optional |
| 4 | GCP project ID | `neon-emitter-458622-e3` |
| 5 | Maps access | Google Maps API via API key (in `.env`, not committed) |
| 6 | Existing discovery agent | Copied into umbrella for self-containment |
| 7 | Python | 3.11, single shared venv at umbrella root |

---

## Folder layout

```
agent_marketplace_demo/
  PLAN.md                       ← this file
  README.md                     ← tutorial-style walkthrough (Phase 6)
  requirements.txt
  .env.example                  ← committed, placeholder values
  .env                          ← gitignored, real values
  .gitignore

  common/                       ← shared helpers
    __init__.py
    auth.py                     ← dynamic Google auth headers
    registry_client.py          ← thin Registry wrapper

  discovery_agent/              ← MCP discovery (adapted from existing repo)
    agent.py
    README.md

  dog_walker_agent/             ← A2A specialist #1
    agent.py                    ← LlmAgent + to_a2a() wrapper
    agent_card.py               ← skills declaration
    buddy.json                  ← hardcoded dog profile
    tools.py                    ← weather, dog profile helpers

  trip_planner_agent/           ← A2A specialist #2
    agent.py
    agent_card.py
    tools.py

  orchestrator_agent/           ← A2A client
    agent.py                    ← uses Registry to route by skill

  deploy/                       ← Phase 7
    deploy_all.sh
    register_maps_mcp.sh
```

---

## Build order

### Phase 0 — Scaffolding
Create the directory structure, `.env`/`.env.example`/`.gitignore`, `requirements.txt`, shared helpers in `common/`, and empty stubs for each agent. Pause and review before Phase 1.

### Phase 1 — DogWalkerAgent core (no A2A yet)
Build the agent as a plain `LlmAgent` with tools (`get_weather` via wttr.in, `get_dog_profile` from buddy.json, Maps MCP toolset). Verify with `python dog_walker_agent/agent.py "Walk Buddy this afternoon"` → produces a real plan.

### Phase 2 — Wrap DogWalker as A2A
Declare three `AgentSkill`s (`plan_walk`, `recommend_dog_park`, `check_walk_conditions`). Wrap with `to_a2a()`. Run as a local A2A server. Verify with `curl localhost:PORT/.well-known/agent.json` and an A2A task call.

### Phase 3 — OrchestratorAgent with Registry discovery
`LlmAgent` whose tool is `discover_and_call_agent(skill_query, prompt)` — calls `registry.search_agents()` → `get_remote_a2a_agent()` → invoke. Verify: `python orchestrator_agent/agent.py "Walk Buddy"` discovers and delegates.

### Phase 4 — TripPlannerAgent (second A2A specialist)
Same shape as DogWalker. Skills: `plan_trip`, `recommend_destination`, `build_itinerary`. Tools: Maps MCP (places, directions), weather, mocked flight data. Verify orchestrator now routes "Plan a weekend in Kyoto" to TripPlanner.

### Phase 5 — Peer-to-peer encore
Give TripPlanner the same `discover_and_call_agent` tool. Update its instruction: if the user mentions a pet, search the Registry for `plan_walk` and arrange care for the trip dates. Verify: "Going to Kyoto next week — what about Buddy?" triggers TripPlanner → DogWalker.

### Phase 6 — Tutorial README
Rewrite root `README.md` as a progressive tutorial matching the four build phases above, with "what if I skipped this?" callouts at each step.

### Phase 7 — Deploy scripts *(optional)*
`agents-cli deploy` for each agent + `register_maps_mcp.sh`. Test against real Agent Runtime in `neon-emitter-458622-e3`.

---

## Scope

### IN scope
- ADK agents with `to_a2a()` wrappers
- Agent cards with skills declarations
- Registry-driven discovery (both A2A and MCP)
- Real APIs (Google Maps, wttr.in)
- Local development mode
- Tutorial-style README

### OUT of scope
- A2A streaming responses (SSE)
- Cross-framework interop (we're ADK-to-ADK)
- Cross-org auth flows
- Long-running task state with task IDs
- Frontend / web UI
- Real flight booking APIs (mock data)
- Test suite

---

## Risks / mitigations

| Risk | Mitigation |
|---|---|
| Google Maps MCP server not in Registry | Register it as part of Phase 1, or fall back to direct Maps SDK |
| Auth / quota issues mid-demo | `MOCK=true` env var on each tool returning cached real responses |
| `to_a2a()` API surface changed | Verify against installed `google-adk` version at Phase 2 start |
| Registry resource names are project-specific | Pull from env vars, never hardcode |
| `wttr.in` rate-limits during repeat demos | Cache response in local file with 10-min TTL |

---

## Estimated effort

| Phases | Scope | Time |
|---|---|---|
| 0–3 | DogWalker + Orchestrator working locally | ~half a day |
| 4–5 | TripPlanner + peer-to-peer | ~2–3 hours |
| 6 | Tutorial README | ~1 hour |
| 7 | Deploy | ~2 hours, skippable initially |
