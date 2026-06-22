"""
agents/critic.py

Day 1: Placeholder node.
Day 5: Real implementation (sandboxed Docker run + LLM verdict + conditional routing).

KEY CONCEPT — THE CONDITIONAL EDGE:
This node's return value determines what happens next in the graph.
The router function (in main.py) reads state["critic"]["current_verdict"]["verdict"]
and routes to either:
  - "cleaner"  (if verdict == "reject" and rounds < max_rounds)
  - "analyst"  (if verdict == "accept")
  - END        (if max rounds exceeded -- fail-safe)

This is a real conditional edge, not if/else in a single node.
LangGraph evaluates it after every Critic run.
"""

from datetime import datetime, timezone
from state.schema import AgentState, CriticState, CriticVerdict, VizEvent
import uuid


def critic_node(state: AgentState) -> dict:
    """
    Placeholder Critic node.
    Real version (Day 5) will:
      - Spin up a Docker container with a copy of the cleaned dataset
      - Run distribution checks (KS test vs. original) inside the container
      - Optionally train a quick model and compare accuracy delta
      - Feed results + cleaning decisions to fine-tuned LLM
      - Return structured CriticVerdict
      - Stream reasoning text as VizEvents for the side panel
    """
    print(f"[Critic] Evaluating round {state['critic']['total_rounds'] + 1}")

    # Placeholder: always accept so the graph can flow end-to-end
    verdict = CriticVerdict(
        verdict_id=str(uuid.uuid4()),
        decision_ids_reviewed=[],
        verdict="accept",               # placeholder -- always accept
        reasoning="[PLACEHOLDER] Critic has not been implemented yet. Auto-accepting.",
        distribution_ok=True,
        model_score_delta=None,
        confidence=0.5,
    )

    event = VizEvent(
        event_id=str(uuid.uuid4()),
        agent="critic",
        event_type="confidence_update",
        payload={"confidence": 0.5, "reasoning": verdict["reasoning"]},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "critic": CriticState(
            verdicts=[verdict],          # operator.add appends
            current_verdict=verdict,     # routing reads this
            total_rounds=state["critic"]["total_rounds"] + 1,
            max_rounds=state["critic"]["max_rounds"],
        ),
        "visualization_events": [event],
    }
