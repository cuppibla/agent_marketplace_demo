# Changelog

Iterative changes during demo development. Latest first.

## 2026-05-16

### Restructured PRESENTATION.md with race-condition as the "before" example
- **Why:** Annie picked Option A from `INTEGRATING_WITH_RACE_CONDITION.md` — open the talk with race-condition, then show the discovery layer it doesn't yet have.
- **What changed:**
  - **Section 0** rewritten: now opens with the hands-up question, then introduces race-condition (banner, architecture diagram, the 🎯 gap slide highlighting "Registry for MCP only, agents are Hub-routed"), then the agenda. Bumped from 2 min → 5 min.
  - **Section 7** got a new closing slide: 🔁 *"Apply this to race-condition"* — visually contrasts today's hardcoded-URL Hub with a Registry-driven Hub. Closes with "race-condition is the chassis; this is the discovery layer."
  - **Pre-show checklist** now includes "have race-condition visual ready" with three options (cached replay, video clip, banner) ordered by risk.
  - **Q&A** added one entry: *"How would I apply this to race-condition?"*
  - **Cheat sheet** updated with Act 0 and the new Act 7 callback.
  - Total runtime: ~26 → ~30 min.
- **Files:** [PRESENTATION.md](./PRESENTATION.md).

### Added integration guide for `race-condition` (Cloud Next '26 keynote demo)
- **Why:** Annie wanted to weave the larger `race-condition` repo into her A2A + Registry talk. After scanning that codebase: it uses A2A heavily across planner / simulator / runner agents, but uses the Agent Registry **only for MCP tool discovery (Maps MCP)**. Agents themselves are wired via a Go Hub with known URLs. That makes it a perfect "before" example to motivate this demo's capability-based A2A discovery story.
- **What's in the guide:** Three integration options (race-condition as "before," as "scale-up payoff," or side-by-side compare), recommendation matrix by audience, and a sketch of how to actually register race-condition's planner in this Registry for a cross-project live demo.
- **Files:** [INTEGRATING_WITH_RACE_CONDITION.md](./INTEGRATING_WITH_RACE_CONDITION.md) (new).

### Strengthened PRESENTATION.md A2A → Registry transition
- **Why:** The original Section 4 ("discovery problem") was a 1-min hand-wave. It didn't *show the pain* of A2A-without-Registry, so the Registry didn't feel earned. Rewrote Section 4 to put hardcoded-URL + `if/elif` orchestrator code on the screen first, then reveal the 2-line Registry equivalent. The "aha" line — *"Registry is the difference between hardcoded routing and capability-based routing"* — got its own slide.
- **Also added:**
  - Skills slide with the "yellow pages vs phone book" framing
  - Honest disclosure about Maps being called directly (not via MCP) in this demo, and what the "pure" MCP version would look like
  - Section 7 "What you'd lose without each piece" table — recaps the value of A2A / Registry / Skills / MCP individually
- **Files:** [PRESENTATION.md](./PRESENTATION.md).

### Standardized all agents on `gemini-3-flash-preview`
- **Why:** TripPlanner's peer-discovery step (find DogWalker via Registry) needed the same instruction-following reliability as the orchestrator. While at it, also upgraded DogWalker and discovery_agent for consistency — all four agents now use the same model so behavior is uniform across the demo.
- **Files:** [dog_walker_agent/agent.py](./dog_walker_agent/agent.py), [trip_planner_agent/agent.py](./trip_planner_agent/agent.py), [discovery_agent/agent.py](./discovery_agent/agent.py).
- **Note:** TripPlanner's peer instruction was also tightened with a worked example (the orchestrator-style "register_search_agents → call_remote_a2a_agent" pattern needs to be spelled out, not just described).

### Switched orchestrator model to `gemini-3-flash-preview`
- **Why:** `gemini-2.5-flash` was inconsistent at following the strict pass-through instruction (sometimes searched the Registry multiple times and gave up before delegating). Pro was reliable but slow. Gemini 3 Flash preview gives Pro-level instruction-following at Flash-level latency.
- **Side effect:** Vertex AI location switched from `us-central1` → `global` (the preview model requires the global endpoint). All current Gemini models support the global endpoint, so other agents are unaffected.
- **Files:** [.env](./.env), [.env.example](./.env.example), [orchestrator_agent/agent.py](./orchestrator_agent/agent.py)

### Tightened orchestrator instruction with a worked example
- **Why:** The "pick ONE topic" rule wasn't enough on its own — the model still sometimes did multiple Registry searches before giving up. Added an explicit example showing how to handle a multi-topic message like *"Going to Kyoto, what about Buddy?"* — orchestrator picks "trip planning" and trusts the TripPlanner specialist to peer-discover DogWalker.
- **Files:** [orchestrator_agent/agent.py](./orchestrator_agent/agent.py)

### Documented the "Registry is just a catalog" model
- **Why:** Easy misconception: assuming Registry entries can only exist if you deploy to Agent Engine. The truth is the Registry is a catalog of pointers — `gcloud agent-registry services create` can register ANY URL (including `localhost`). Deploy to Agent Engine is one way to populate the Registry; manual registration is another.
- **Files:** [README.md](./README.md) (added "How the Registry actually works" section), [DEMO.md](./DEMO.md) (expanded "Common questions"), this CHANGELOG.

### Polished DogWalker for multi-day requests
- **Why:** When called for "while away" or multi-day care, DogWalker was declining ("I can only plan one walk"). Updated instruction to handle Case A (single walk) vs Case B (extended absence — propose a daily routine).
- **Files:** [dog_walker_agent/agent.py](./dog_walker_agent/agent.py)

### Switched Maps from API key to ADC + new APIs
- **Why:** API key required per-key API restrictions to be configured. ADC + Places API (New) + Routes API uses the same auth as everything else (`gcloud auth application-default login`), no per-key setup.
- **Files:** [dog_walker_agent/tools.py](./dog_walker_agent/tools.py), [trip_planner_agent/tools.py](./trip_planner_agent/tools.py), [pyproject.toml](./pyproject.toml) (removed `googlemaps`).

### Separated Vertex region from Registry region
- **Why:** Registry uses `global` location; Vertex needs a real region. Originally a single `GOOGLE_CLOUD_LOCATION` env var conflicted. Split into `GOOGLE_CLOUD_LOCATION` (Vertex) and `AGENT_REGISTRY_LOCATION` (Registry). After switching to `gemini-3-flash-preview`, both end up using `global` again — but the separation is preserved for clarity.
- **Files:** [.env](./.env), [common/registry_client.py](./common/registry_client.py)
