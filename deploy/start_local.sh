#!/usr/bin/env bash
# Start the two A2A servers in the background, then register them in the Registry.
# Run from the project root: ./deploy/start_local.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# Source env so PORTS are available
set -a
# shellcheck disable=SC1091
source .env
set +a

mkdir -p .cache
echo "→ Starting DogWalker on :${DOG_WALKER_PORT:-8001}"
uv run python dog_walker_agent/server.py > .cache/dog_walker.log 2>&1 &
echo $! > .cache/dog_walker.pid

echo "→ Starting TripPlanner on :${TRIP_PLANNER_PORT:-8002}"
uv run python trip_planner_agent/server.py > .cache/trip_planner.log 2>&1 &
echo $! > .cache/trip_planner.pid

echo "→ Waiting for both agent cards to be reachable..."
for port in "${DOG_WALKER_PORT:-8001}" "${TRIP_PLANNER_PORT:-8002}"; do
    until curl -fs "http://localhost:${port}/.well-known/agent-card.json" -o /dev/null 2>/dev/null; do
        sleep 1
    done
    echo "  ✓ :${port} ready"
done

echo "→ Registering both agents in the Agent Registry..."
uv run python dog_walker_agent/register.py
uv run python trip_planner_agent/register.py

cat <<EOF

✓ Both agents are up and registered.

  DogWalker:    http://localhost:${DOG_WALKER_PORT:-8001}   (logs: .cache/dog_walker.log)
  TripPlanner:  http://localhost:${TRIP_PLANNER_PORT:-8002}   (logs: .cache/trip_planner.log)

Try the orchestrator:
  uv run python orchestrator_agent/agent.py "Walk Buddy this afternoon"
  uv run python orchestrator_agent/agent.py "Plan a 2-day trip to Kyoto, what about Buddy?"

Stop with:
  ./deploy/stop_local.sh
EOF
