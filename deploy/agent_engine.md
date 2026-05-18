# Deploying to Vertex AI Agent Engine

When you're ready to move beyond `localhost`, deploy each A2A agent to **Vertex AI Agent Engine**. Once deployed, the Agent Registry **auto-discovers and indexes the agent's skills** from its agent card — no manual `register.py` step needed.

This file is intentionally documentation, not an automated script: deploying to Agent Engine creates billable resources and a one-size-fits-all script would hide too much detail. Use these commands as a starting point and adapt to your CI/CD.

---

## Prerequisites

- Vertex AI API enabled (`aiplatform.googleapis.com`) — already enabled if you ran the Setup section of the root README.
- IAM role: `roles/aiplatform.user` and `roles/agentregistry.serviceAdmin` on your account.
- A Cloud Storage bucket for staging (created with `gcloud storage buckets create`).

---

## Deploy DogWalker

```bash
cd dog_walker_agent

uv run adk deploy agent-engine \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --staging-bucket=gs://<your-staging-bucket> \
  --display-name="DogWalkerAgent" \
  --requirements-file=../pyproject.toml \
  .
```

This packages `dog_walker_agent/`, builds a container, and deploys to Agent Engine. The deployment becomes an A2A-compatible endpoint, and **Agent Registry automatically scrapes its agent card** within a few minutes.

Verify:

```bash
gcloud alpha agent-registry agents list --location=global --project=$GOOGLE_CLOUD_PROJECT
# → dog_walker_agent (deployed) appears with all three skills indexed
```

---

## Deploy TripPlanner

Same shape:

```bash
cd trip_planner_agent

uv run adk deploy agent-engine \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --staging-bucket=gs://<your-staging-bucket> \
  --display-name="TripPlannerAgent" \
  --requirements-file=../pyproject.toml \
  .
```

---

## What changes for the Orchestrator

**Nothing in the code.** The orchestrator already discovers agents via `registry_search_agents`. The Registry now returns the deployed Agent Engine URLs instead of `localhost:8001/8002`, and the same `call_remote_a2a_agent` helper works — that's the whole point of capability-based discovery.

The only thing to remove is the manual `register.py` step from your start scripts. Auto-registration replaces it.

---

## Cleanup

```bash
# List deployments
gcloud ai reasoning-engines list --region=$GOOGLE_CLOUD_LOCATION --project=$GOOGLE_CLOUD_PROJECT

# Delete by resource name
gcloud ai reasoning-engines delete <RESOURCE_NAME> --region=$GOOGLE_CLOUD_LOCATION --project=$GOOGLE_CLOUD_PROJECT
```

The Registry entries are removed automatically when the deployment is deleted.

---

## Alternative: Cloud Run

If you want more control (custom container, GPU, scale-to-zero settings), deploy the A2A server image directly to Cloud Run, then register the resulting URL with `register.py`. This is the same flow as local dev, just with a public HTTPS URL instead of `localhost`.

```bash
gcloud run deploy dog-walker --source=dog_walker_agent --region=$GOOGLE_CLOUD_LOCATION
# → outputs https URL
# Update .env: DOG_WALKER_HOST=<run-hostname>, DOG_WALKER_PORT=443
uv run python dog_walker_agent/register.py
```

Cloud Run deployments do not auto-register in the Agent Registry — that's an Agent Engine convenience. Use `register.py` to bridge.
