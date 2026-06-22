"""
agents/profiler.py

Day 1: Placeholder node.
Day 2: Real implementation (pandas profiling, LLM issue description, ChromaDB retrieval).

HOW A LANGGRAPH NODE WORKS:
- Receives the full AgentState as input.
- Returns a PARTIAL dict of only the keys it changed.
- LangGraph merges the partial return into state automatically.
- NEVER return the full state -- that defeats the merge mechanism.
"""

from datetime import datetime, timezone
from state.schema import AgentState, ProfilerState, VizEvent
import uuid


def profiler_node(state: AgentState) -> dict:
    """
    Placeholder Profiler node.
    Real version (Day 2) will:
      - Load the dataset from state["input"]["dataset_path"]
      - Compute per-column stats (null %, dtype, unique count, IQR for outliers)
      - Query ChromaDB for similar past issues
      - Ask LLM to describe each issue in natural language
      - Emit VizEvents to flag cells amber in the UI
    """
    print(f"[Profiler] Running on: {state['input']['dataset_name']}")

    # Emit a viz event so the frontend knows the profiler ran
    event = VizEvent(
        event_id=str(uuid.uuid4()),
        agent="profiler",
        event_type="round_complete",
        payload={"message": "Profiler placeholder complete. No real issues detected yet."},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Return ONLY the keys this agent touched
    return {
        "profiler": ProfilerState(
            run_complete=True,
            row_count=0,
            column_count=0,
            issues=[],
            profile_summary="[PLACEHOLDER] Profiler has not been implemented yet.",
            column_stats={},
        ),
        "visualization_events": [event],  # operator.add will append this
    }
