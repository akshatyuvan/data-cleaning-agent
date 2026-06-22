"""
tests/test_graph.py

Tests for the graph skeleton. Uses placeholder nodes (no LLM calls).
Run: pytest tests/test_graph.py -v
"""

import pytest
from main import build_graph, run_pipeline
from state.schema import make_initial_state


def test_graph_builds_without_error():
    """The graph should compile without exceptions."""
    graph = build_graph()
    assert graph is not None


def test_graph_runs_end_to_end():
    """
    With placeholder nodes, the graph should run start-to-finish
    and return a final state with all expected keys.
    """
    result = run_pipeline(
        dataset_path="data/raw/fake.csv",   # file doesn't need to exist yet
        dataset_name="test_run",
    )

    # Should have completed
    assert result["analyst"]["run_complete"] is True
    assert result["profiler"]["run_complete"] is True


def test_critic_placeholder_accepts_and_does_not_loop():
    """
    Placeholder Critic always returns 'accept'.
    Verify the graph exits after 1 round, not stuck in a loop.
    """
    result = run_pipeline("fake.csv", "loop_test")
    assert result["critic"]["total_rounds"] == 1


def test_viz_events_are_accumulated():
    """
    Each placeholder agent emits one VizEvent.
    With 4 agents, we should have at least 4 events.
    """
    result = run_pipeline("fake.csv", "viz_test")
    assert len(result["visualization_events"]) >= 4


def test_errors_list_is_empty_on_clean_run():
    """No errors should be recorded in a placeholder run."""
    result = run_pipeline("fake.csv", "error_test")
    assert result["errors"] == []
