"""A2A Agent Card for DogWalkerAgent.

The Agent Card is served at /.well-known/agent.json once the agent is
running as an A2A server. The Google Cloud Agent Registry scrapes this
card on deploy and indexes each skill's description + tags for search.

Three narrow skills (instead of one big "does dog stuff") so other agents
can discover us by *capability*, not by name.
"""

import os

from a2a.types import AgentCapabilities, AgentCard, AgentSkill


def build_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="dog_walker_agent",
        description=(
            "Plans personalized dog walks using real maps and weather data. "
            "Reasons about the dog's breed, energy level, and heat tolerance, "
            "then composes a walking route from nearby parks."
        ),
        version="1.0.0",
        url=f"http://{host}:{port}/",
        protocol_version="0.3.0",
        preferred_transport="JSONRPC",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        skills=[
            AgentSkill(
                id="plan_walk",
                name="Plan Dog Walk",
                description=(
                    "Plan a walking route for a dog given a home address and "
                    "optional time budget. Considers weather, dog energy level, "
                    "and route variety. Returns a route with map URL."
                ),
                tags=["dog", "walk", "route", "pet", "exercise", "planning"],
                examples=[
                    "Walk Buddy for 30 minutes near Mission, SF",
                    "Plan an afternoon walk for my Lab",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="recommend_dog_park",
                name="Recommend Dog Park",
                description=(
                    "Recommend the best nearby dog park given the dog's profile "
                    "and current weather conditions. Returns a ranked list."
                ),
                tags=["dog", "park", "recommendation", "pet"],
                examples=[
                    "Best dog park near Mission SF on a hot afternoon",
                    "Where should I take my high-energy Lab?",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="check_walk_conditions",
                name="Check Walk Conditions",
                description=(
                    "Assess whether it's a safe and pleasant time to walk a dog. "
                    "Considers temperature, precipitation, heat index for paws, "
                    "and breed-specific tolerances."
                ),
                tags=["dog", "weather", "safety", "pet", "heat"],
                examples=[
                    "Is it OK to walk a husky in SF right now?",
                    "Should I walk my dog this afternoon?",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
        ],
    )
