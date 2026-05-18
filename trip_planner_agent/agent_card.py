"""A2A Agent Card for TripPlannerAgent."""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill


def build_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="trip_planner_agent",
        description=(
            "Plans short city trips using real maps and weather. Reasons about "
            "geography, weather, and traveler interests to build a day-by-day "
            "itinerary of real attractions and walking routes."
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
                id="plan_trip",
                name="Plan Trip",
                description=(
                    "Plan a short city trip given a destination, duration, and "
                    "traveler interests. Returns a day-by-day itinerary with "
                    "real attractions and walking time estimates."
                ),
                tags=["trip", "travel", "itinerary", "vacation", "planning", "city"],
                examples=[
                    "Plan a 2-day trip to Kyoto for a foodie",
                    "Weekend in Lisbon with a focus on architecture",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="recommend_destination",
                name="Recommend Destination",
                description=(
                    "Suggest travel destinations given the traveler's interests, "
                    "time of year, and trip length."
                ),
                tags=["trip", "travel", "destination", "recommendation"],
                examples=[
                    "Where should I go for a relaxing 3-day beach trip in October?",
                    "Suggest a European city for foodies in spring",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="build_itinerary",
                name="Build Itinerary",
                description=(
                    "Build a day-by-day itinerary for a given destination and "
                    "duration, grouping attractions geographically and noting "
                    "walking distances."
                ),
                tags=["trip", "itinerary", "schedule", "travel"],
                examples=[
                    "Build a 3-day itinerary for Tokyo",
                    "Day-by-day plan for 4 days in Rome",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
        ],
    )
