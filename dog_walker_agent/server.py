"""Serve DogWalkerAgent as an A2A server.

Run:
    uv run python dog_walker_agent/server.py
    # or override port:
    DOG_WALKER_PORT=8001 uv run python dog_walker_agent/server.py

Then inspect the agent card:
    curl http://localhost:8001/.well-known/agent-card.json
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import uvicorn

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from dog_walker_agent.agent import root_agent
from dog_walker_agent.agent_card import build_agent_card


def main():
    host = os.environ.get("DOG_WALKER_HOST", "localhost")
    port = int(os.environ.get("DOG_WALKER_PORT", "8001"))

    app = to_a2a(
        root_agent,
        host=host,
        port=port,
        agent_card=build_agent_card(host, port),
    )

    print(f"DogWalker A2A server starting at http://{host}:{port}")
    print(f"  Agent card: http://{host}:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
