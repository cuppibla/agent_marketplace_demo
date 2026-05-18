#!/usr/bin/env bash
# Stop the local A2A servers started by start_local.sh.
# Optionally also deregister them from the Agent Registry.

set -euo pipefail

cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source .env
set +a

for name in dog_walker trip_planner; do
    pidfile=".cache/${name}.pid"
    if [[ -f "$pidfile" ]]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo "→ Killing ${name} (pid ${pid})"
            kill "$pid"
        fi
        rm -f "$pidfile"
    fi
done

# Belt-and-suspenders: also kill anything listening on the ports.
for port in "${DOG_WALKER_PORT:-8001}" "${TRIP_PLANNER_PORT:-8002}"; do
    if pids=$(lsof -ti:"$port" 2>/dev/null); then
        echo "→ Freeing port ${port} (pids: ${pids})"
        echo "$pids" | xargs kill -9
    fi
done

if [[ "${1:-}" == "--deregister" ]]; then
    echo "→ Deregistering services from Agent Registry..."
    for service in dog-walker-agent trip-planner-agent; do
        gcloud alpha agent-registry services delete \
            "projects/${GOOGLE_CLOUD_PROJECT}/locations/${AGENT_REGISTRY_LOCATION:-global}/services/${service}" \
            --quiet 2>&1 || echo "  (${service} not registered, skipping)"
    done
fi

echo "✓ Done."
