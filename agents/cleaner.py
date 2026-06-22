"""
agents/cleaner.py

Day 1: Placeholder node.
Day 3: Real implementation (LLM proposes actions, pandas applies them, decisions logged).
"""

from datetime import datetime, timezone
from state.schema import AgentState, CleanerState, VizEvent
import uuid


def cleaner_node(state: AgentState) -> dict:
    """
    Placeholder Cleaning node.
    Real version (Day 3) will:
      - Iterate over state["profiler"]["issues"]
      - For each issue, ask LLM: "Given this issue and context, what action do you propose?"
      - Apply the action via pandas
      - Log a CleaningDecision with full justification text
      - Emit VizEvents (blue flash per cell acted on)
    """
    print(f"[Cleaner] Round {state['cleaner']['current_round'] + 1}")

    event = VizEvent(
        event_id=str(uuid.uuid4()),
        agent="cleaner",
        event_type="round_complete",
        payload={"message": "Cleaner placeholder complete. No decisions made yet."},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "cleaner": CleanerState(
            current_round=state["cleaner"]["current_round"] + 1,
            decisions=[],          # operator.add accumulates across rounds
            dataset_snapshot_path=None,
        ),
        "visualization_events": [event],
    }
