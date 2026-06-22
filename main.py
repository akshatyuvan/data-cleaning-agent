"""
main.py  —  Builds and runs the LangGraph agent graph.

LANGGRAPH CONCEPTS USED HERE:
------------------------------
StateGraph:
  - The graph object. You add nodes and edges to it, then compile it.
  - Compiled graph is what you actually invoke.

add_node(name, function):
  - Registers a node. The function signature must be: fn(state: AgentState) -> dict

add_edge(from, to):
  - Hard/unconditional edge. Always goes from -> to.

add_conditional_edges(from, router_fn, mapping):
  - After `from` node runs, calls router_fn(state) to get a string key.
  - Looks up that key in `mapping` to find the next node name.
  - THIS is the mechanism that makes the Critic's redo loop real.

START / END:
  - Special sentinel nodes from LangGraph. Graph begins at START, terminates at END.

GRAPH FLOW (Day 1 placeholder):
  START -> profiler -> cleaner -> critic --[accept]--> analyst -> END
                          ^                |
                          |___[reject]_____|
                          (redo loop, up to max_rounds times)
"""

from langgraph.graph import StateGraph, START, END

from state.schema import AgentState, make_initial_state
from agents.profiler import profiler_node
from agents.cleaner import cleaner_node
from agents.critic import critic_node
from agents.analyst import analyst_node


# ---------------------------------------------------------
# ROUTER FUNCTION  —  this is what makes it truly agentic
# ---------------------------------------------------------

def critic_router(state: AgentState) -> str:
    """
    Called by LangGraph after the Critic node runs.
    Returns a string key that maps to the next node.

    Why this is important for interviews:
    - This is NOT an if/else in the Critic node itself.
    - LangGraph evaluates this function AFTER the node returns.
    - The graph topology itself is dynamic -- the path through the graph
      is determined at runtime based on state, not hardcoded at build time.
    - This is the definition of a real conditional edge.
    """
    verdict = state["critic"]["current_verdict"]
    total_rounds = state["critic"]["total_rounds"]
    max_rounds = state["critic"]["max_rounds"]

    if verdict is None:
        # Should never happen, but fail safe
        print("[Router] WARNING: No verdict found, defaulting to analyst")
        return "go_to_analyst"

    if verdict["verdict"] == "accept":
        print(f"[Router] Critic accepted after {total_rounds} round(s). Moving to Analyst.")
        return "go_to_analyst"

    if total_rounds >= max_rounds:
        # Safety valve: don't loop forever
        print(f"[Router] Max rounds ({max_rounds}) reached. Forcing analyst with caveats.")
        return "go_to_analyst"

    # Critic rejected -- send back to Cleaner for another round
    print(f"[Router] Critic rejected. Sending back to Cleaner (round {total_rounds + 1}).")
    return "go_to_cleaner"


# ---------------------------------------------------------
# GRAPH BUILDER
# ---------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Constructs the agent graph. Returns the compiled graph ready to invoke.

    Separation note: build_graph() only wires structure.
    Node logic lives in agents/*.py.
    State schema lives in state/schema.py.
    This function is pure plumbing.
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("profiler", profiler_node)
    graph.add_node("cleaner", cleaner_node)
    graph.add_node("critic", critic_node)
    graph.add_node("analyst", analyst_node)

    # Unconditional edges
    graph.add_edge(START, "profiler")       # graph always starts at profiler
    graph.add_edge("profiler", "cleaner")   # profiler always hands off to cleaner
    graph.add_edge("cleaner", "critic")     # cleaner always hands off to critic

    # THE CONDITIONAL EDGE  (the core agentic mechanism)
    graph.add_conditional_edges(
        "critic",           # after this node runs...
        critic_router,      # ...call this function to get a routing key...
        {                   # ...and map the key to the next node
            "go_to_analyst": "analyst",
            "go_to_cleaner": "cleaner",
        }
    )

    # Analyst is always the terminal node
    graph.add_edge("analyst", END)

    return graph.compile()


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

def run_pipeline(
    dataset_path: str,
    dataset_name: str = "my_dataset",
    target_column: str | None = None,
) -> AgentState:
    """
    Main entry point. Build the graph, run it, return final state.
    FastAPI will call this (Day 8+). For now, run directly.
    """
    graph = build_graph()

    initial_state = make_initial_state(
        dataset_path=dataset_path,
        dataset_name=dataset_name,
        target_column=target_column,
    )

    print(f"\n{'='*60}")
    print(f"Starting pipeline for: {dataset_name}")
    print(f"Session: {initial_state['metadata']['session_id']}")
    print(f"{'='*60}\n")

    final_state = graph.invoke(initial_state)

    print(f"\n{'='*60}")
    print("Pipeline complete.")
    print(f"Viz events emitted: {len(final_state['visualization_events'])}")
    print(f"Errors recorded: {len(final_state['errors'])}")
    print(f"{'='*60}\n")

    return final_state


if __name__ == "__main__":
    # Quick smoke test — runs with a fake path since Profiler is placeholder
    result = run_pipeline(
        dataset_path="data/raw/sample.csv",
        dataset_name="smoke_test",
    )
    print("Final analyst summary:", result["analyst"]["analysis_summary"])
    print("Critic rounds:", result["critic"]["total_rounds"])
