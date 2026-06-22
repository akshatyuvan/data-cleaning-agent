"""
state/schema.py  —  The single source of truth for what every agent can read/write.

WHY NESTED, NOT FLAT?
---------------------
A flat dict looks tempting at first:
    state = {"missing_pct": 0.3, "issues": [...], "cleaning_log": [...], ...}

But as your graph grows you get:
- Name collisions:  which agent wrote "confidence"? The Critic or the Analyst?
- Unclear ownership: can the Cleaning agent write to "profile_summary"? Should it?
- No IDE help:      state["profiel_summary"] fails silently at runtime, not at type-check

Nested TypedDicts give you:
- One sub-dict per agent → clear ownership, easy to reason about
- Pydantic-style validation at the edges
- LangGraph's reducer system works cleanly per sub-key
- When you add a new agent later, you add one new key — nothing else breaks

LANGGRAPH STATE BASICS (learn this once, use it everywhere):
- LangGraph passes the full `AgentState` dict into every node function.
- Each node returns a PARTIAL dict — only the keys it changed.
- LangGraph merges partial returns back into the full state automatically.
- `Annotated[list, operator.add]` means "append to this list" instead of replace.
  Use it for logs, history, issues — anything accumulating across multiple steps.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict


# ---------------------------------------------------------
# SUB-SCHEMAS  (one per agent domain)
# ---------------------------------------------------------

class DataIssue(TypedDict):
    """
    A single data quality problem found by the Profiler.
    Structured so the Cleaning agent can act on it directly.
    """
    issue_id: str                   # e.g. "issue_001"
    column: str                     # which column has the problem
    issue_type: Literal[            # controlled vocab prevents typos
        "missing_values",
        "type_mismatch",
        "outlier",
        "duplicate_rows",
        "inconsistent_category",
        "unknown"
    ]
    severity: Literal["low", "medium", "high"]
    affected_rows: int              # how many rows are impacted
    detail: str                     # human-readable description
    suggested_fix: Optional[str]    # Profiler's hint, Cleaner can override


class ProfilerState(TypedDict):
    """
    Output produced by the Profiler agent.
    Written once; read by Cleaner and ChromaDB retrieval.
    """
    run_complete: bool
    row_count: int
    column_count: int
    issues: list[DataIssue]         # list of all detected problems
    profile_summary: str            # natural language summary for LLM context
    column_stats: dict[str, Any]    # {col: {dtype, null_pct, unique_count, ...}}


class CleaningDecision(TypedDict):
    """
    One cleaning action proposed and applied by the Cleaning agent.
    Must include justification — this is what the Critic evaluates.
    """
    decision_id: str                # e.g. "decision_001"
    issue_id: str                   # links back to DataIssue.issue_id
    column: str
    action: Literal[
        "impute_mean",
        "impute_median",
        "impute_mode",
        "impute_constant",
        "drop_rows",
        "drop_column",
        "type_cast",
        "standardize_category",
        "flag_outlier",
        "no_action"
    ]
    parameters: dict[str, Any]      # e.g. {"fill_value": 0} or {"target_type": "int"}
    justification: str              # WHY this action — what the Critic reads
    status: Literal[
        "proposed",
        "applied",
        "rejected",
        "redo_requested"
    ]
    redo_count: int                 # how many times Critic sent this back


class CleanerState(TypedDict):
    """
    Output produced by the Cleaning agent across (potentially multiple) rounds.
    `decisions` uses operator.add so each round appends, not overwrites.
    """
    current_round: int
    decisions: Annotated[list[CleaningDecision], operator.add]
    dataset_snapshot_path: Optional[str]   # path to parquet of cleaned-so-far


class CriticVerdict(TypedDict):
    """
    The Critic's evaluation of one or more CleaningDecisions.
    This is the signal that drives the conditional edge in LangGraph.
    """
    verdict_id: str
    decision_ids_reviewed: list[str]
    verdict: Literal["accept", "reject", "partial_accept"]
    reasoning: str                  # streamed live in the UI
    distribution_ok: bool           # did distributions stay reasonable?
    model_score_delta: Optional[float]  # quick downstream check (Day 5+)
    confidence: float               # 0.0-1.0, drives the arc in the UI


class CriticState(TypedDict):
    """
    Accumulated output of the Critic across all rounds.
    Uses operator.add so verdict history is preserved for the Analyst.
    """
    verdicts: Annotated[list[CriticVerdict], operator.add]
    current_verdict: Optional[CriticVerdict]  # latest one, for routing
    total_rounds: int
    max_rounds: int                 # safety cap -- prevents infinite redo loops


class Insight(TypedDict):
    """One finding from the Analyst, with an explicit trustworthiness label."""
    insight_id: str
    finding: str
    trustworthiness: Literal["high", "medium", "low"]
    reason_for_rating: str          # e.g. "3 of 5 values in this column were imputed"


class AnalystState(TypedDict):
    """Output of the Analyst agent, only populated after Critic accepts."""
    run_complete: bool
    insights: list[Insight]
    analysis_summary: str


# ---------------------------------------------------------
# TOP-LEVEL STATE  (what LangGraph sees)
# ---------------------------------------------------------

class AgentState(TypedDict):
    """
    The single state object threaded through the entire graph.

    Design rules:
    1. `input` and analyst are top-level exit points -- easy to find.
    2. Each agent owns exactly one sub-dict. No agent writes to another's.
    3. `metadata` holds config/session info: readable, not mutable by agents.
    4. `errors` uses operator.add so any node can append without overwriting.
    5. `visualization_events` is the bus for the frontend. Agents push events;
       the viz layer reads them. Clean separation of concerns.
    """

    # Entry point
    input: InputState

    # Per-agent namespaces
    profiler: ProfilerState
    cleaner: CleanerState
    critic: CriticState
    analyst: AnalystState

    # Cross-cutting concerns
    metadata: MetadataState
    errors: Annotated[list[ErrorRecord], operator.add]

    # Frontend event bus (visualization layer reads this)
    visualization_events: Annotated[list[VizEvent], operator.add]


class InputState(TypedDict):
    """
    Provided at graph invocation time. Never mutated after that.
    """
    dataset_path: str               # path to the raw messy CSV / parquet
    dataset_name: str               # human label for logs/UI
    target_column: Optional[str]    # for downstream eval (Day 9+), can be None


class MetadataState(TypedDict):
    """
    Session-level config. Set once at invocation; agents read but don't write.
    """
    session_id: str
    started_at: str                 # ISO timestamp
    max_critic_rounds: int          # cap for the redo loop (default 3)
    llm_model: str                  # e.g. "gpt-4o-mini" or fine-tuned model path
    chroma_collection: str          # which ChromaDB collection to query


class ErrorRecord(TypedDict):
    """Structured error -- any node can append one of these to state['errors']."""
    agent: str                      # which agent raised this
    error_type: str                 # e.g. "docker_timeout", "llm_parse_error"
    message: str
    timestamp: str
    recoverable: bool               # can the graph continue, or must it halt?


class VizEvent(TypedDict):
    """
    Events pushed by agents for the visualization layer to consume.
    Agents don't know about the UI -- they just emit structured events.
    The viz layer decides how to render them.

    cell_status values map to UI colors:
      "untouched"  -> grey
      "flagged"    -> amber
      "cleaning"   -> blue flash
      "rejected"   -> red flash -> back to amber
      "verified"   -> green
    """
    event_id: str
    agent: Literal["profiler", "cleaner", "critic", "analyst"]
    event_type: Literal[
        "cell_status_change",
        "critic_reasoning_chunk",   # streamed text for side panel
        "confidence_update",        # drives the arc widget
        "round_complete"
    ]
    payload: dict[str, Any]         # {col, row, status} or {text_chunk} etc.
    timestamp: str


# ---------------------------------------------------------
# INITIALIZER  -- creates a valid empty state
# ---------------------------------------------------------

def make_initial_state(
    dataset_path: str,
    dataset_name: str,
    session_id: str = "",
    target_column: Optional[str] = None,
    llm_model: str = "gpt-4o-mini",
    max_critic_rounds: int = 3,
    chroma_collection: str = "data_quality_patterns",
) -> AgentState:
    """
    Returns a fully-initialized AgentState with sensible defaults.
    Call this before invoking the graph -- never build state by hand in tests.

    Having a single factory function means:
    - You never forget to initialize a field (KeyError in a node = hours of debug)
    - Tests always start from a known-good baseline
    - Adding a new field? Add it here once; everywhere benefits immediately.
    """
    import uuid
    from datetime import datetime, timezone

    return AgentState(
        input=InputState(
            dataset_path=dataset_path,
            dataset_name=dataset_name,
            target_column=target_column,
        ),
        profiler=ProfilerState(
            run_complete=False,
            row_count=0,
            column_count=0,
            issues=[],
            profile_summary="",
            column_stats={},
        ),
        cleaner=CleanerState(
            current_round=0,
            decisions=[],
            dataset_snapshot_path=None,
        ),
        critic=CriticState(
            verdicts=[],
            current_verdict=None,
            total_rounds=0,
            max_rounds=max_critic_rounds,
        ),
        analyst=AnalystState(
            run_complete=False,
            insights=[],
            analysis_summary="",
        ),
        metadata=MetadataState(
            session_id=session_id or str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
            max_critic_rounds=max_critic_rounds,
            llm_model=llm_model,
            chroma_collection=chroma_collection,
        ),
        errors=[],
        visualization_events=[],
    )
