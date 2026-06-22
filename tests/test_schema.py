"""
tests/test_schema.py

Tests for the state schema. Run: pytest tests/test_schema.py -v
These tests are fast (no LLM calls) and should stay that way.
"""

import pytest
from state.schema import (
    make_initial_state,
    AgentState,
    DataIssue,
    CleaningDecision,
    CriticVerdict,
)


def test_make_initial_state_has_all_keys():
    """make_initial_state must return a dict with all top-level keys."""
    state = make_initial_state(
        dataset_path="data/raw/test.csv",
        dataset_name="test_dataset",
    )
    required_keys = {"input", "profiler", "cleaner", "critic", "analyst",
                     "metadata", "errors", "visualization_events"}
    assert required_keys.issubset(state.keys()), (
        f"Missing keys: {required_keys - set(state.keys())}"
    )


def test_initial_state_profiler_not_complete():
    """Profiler should start as not complete."""
    state = make_initial_state("x.csv", "x")
    assert state["profiler"]["run_complete"] is False


def test_initial_state_errors_is_empty_list():
    """Errors must be an empty list, not None."""
    state = make_initial_state("x.csv", "x")
    assert state["errors"] == []


def test_initial_state_viz_events_is_empty_list():
    """Viz events must be an empty list, not None."""
    state = make_initial_state("x.csv", "x")
    assert state["visualization_events"] == []


def test_initial_state_critic_rounds():
    """Critic should start at 0 rounds with configurable max."""
    state = make_initial_state("x.csv", "x", max_critic_rounds=5)
    assert state["critic"]["total_rounds"] == 0
    assert state["critic"]["max_rounds"] == 5


def test_initial_state_session_id_is_not_empty():
    """A session ID should always be generated."""
    state = make_initial_state("x.csv", "x")
    assert len(state["metadata"]["session_id"]) > 0


def test_custom_session_id_is_preserved():
    """If you pass a session_id it should be kept."""
    state = make_initial_state("x.csv", "x", session_id="my-session-123")
    assert state["metadata"]["session_id"] == "my-session-123"


def test_target_column_optional():
    """target_column defaults to None and can be set."""
    s1 = make_initial_state("x.csv", "x")
    assert s1["input"]["target_column"] is None

    s2 = make_initial_state("x.csv", "x", target_column="price")
    assert s2["input"]["target_column"] == "price"
