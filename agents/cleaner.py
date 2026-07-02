"""
agents/cleaner.py

Day 1: Placeholder node.
Day 3: Real implementation (LLM proposes actions, pandas applies them, decisions logged).

UPDATED: now sets current_active_agent + pipeline_steps_run, required for
the shared Critic + Orchestrator routing to work correctly.
"""

from datetime import datetime, timezone
from state.schema import AgentState, CleanerState, VizEvent, MetadataState
import uuid


def cleaner_node(state: AgentState) -> dict:
    print(f"[Cleaner] Round {state['cleaner']['current_round'] + 1}")

    event = VizEvent(
        event_id=str(uuid.uuid4()),
        agent="cleaner",
        event_type="round_complete",
        payload={"message": "Cleaner placeholder complete. No decisions made yet."},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Mark this agent as active, and record that it has run (for orchestrator + critic)
    updated_metadata = dict(state["metadata"])
    updated_metadata["current_active_agent"] = "cleaner"
    if "cleaner" not in updated_metadata["pipeline_steps_run"]:
        updated_metadata["pipeline_steps_run"] = updated_metadata["pipeline_steps_run"] + ["cleaner"]

    return {
        "cleaner": CleanerState(
            current_round=state["cleaner"]["current_round"] + 1,
            decisions=[],
            dataset_snapshot_path=None,
        ),
        "metadata": updated_metadata,
        "visualization_events": [event],
    }
