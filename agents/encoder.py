"""
agents/encoder.py
Placeholder. Real implementation: Day 7.
"""
from datetime import datetime, timezone
from state.schema import AgentState, EncodingState, VizEvent
import uuid

def encoder_node(state: AgentState) -> dict:
    print("[Encoder] Running (placeholder)")

    event = VizEvent(
        event_id=str(uuid.uuid4()),
        agent="encoder",
        event_type="round_complete",
        payload={"message": "Encoder placeholder complete."},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    updated_metadata = dict(state["metadata"])
    updated_metadata["current_active_agent"] = "encoder"
    if "encoder" not in updated_metadata["pipeline_steps_run"]:
        updated_metadata["pipeline_steps_run"] = updated_metadata["pipeline_steps_run"] + ["encoder"]

    return {
        "encoder": EncodingState(run_complete=True, decisions=[], dataset_snapshot_path=None),
        "metadata": updated_metadata,
        "visualization_events": [event],
    }