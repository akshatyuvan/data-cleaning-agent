"""
main.py  --  Builds and runs the LangGraph agent graph.

UPDATED FOR: 4 new preprocessing agents + shared Critic + Orchestrator routing.

GRAPH FLOW (current):
  START -> profiler -> orchestrator_router -> {cleaner | encoder | scaler |
                                                imbalance_handler |
                                                feature_selector | analyst}
                              ^                         |
                              |                         v
                       (loop back here            each agent -> critic
                        after each agent                |
                        completes a step)         critic_router
                                                    /          \
                                              accept            reject
                                                |                  |
                                    back to orchestrator    back to SAME
                                    (picks next step)        agent (redo)

KEY DESIGN: critic is ONE shared node. After it runs, critic_router decides
accept/reject. On accept, control returns to orchestrator_router, which
decides the NEXT step (not analyst directly -- only goes to analyst once
all requested steps are done). On reject, control goes back to whichever
agent just ran, for a redo.
"""

from langgraph.graph import StateGraph, START, END

from state.schema import AgentState, make_initial_state
from agents.profiler import profiler_node
from agents.cleaner import cleaner_node
from agents.encoder import encoder_node
from agents.scaler import scaler_node
from agents.imbalance_handler import imbalance_handler_node
from agents.feature_selector import feature_selector_node
from agents.critic import critic_node
from agents.analyst import analyst_node


# ---------------------------------------------------------
# ROUTER FUNCTIONS
# ---------------------------------------------------------

def orchestrator_router(state: AgentState) -> str:
    """
    Decides which preprocessing agent runs next based on requested_steps,
    auto-including dependencies, and skipping unrequested steps entirely.

    Called in TWO places in the graph:
    1. Right after the Profiler (to pick the FIRST step)
    2. After the Critic accepts a step (to pick the NEXT step)
    Same function, same logic, because "what's the next undone requested
    step" is identical in both cases.
    """
    steps = state["input"]["requested_steps"]
    pipeline_steps_run = state["metadata"]["pipeline_steps_run"]

    # Dependency rule: encoding/scaling/feature_selection need cleaning first
    needs_cleaning = steps["encoding"] or steps["scaling"] or steps["feature_selection"]
    if needs_cleaning and not steps["cleaning"] and "cleaner" not in pipeline_steps_run:
        return "go_to_cleaner"  # auto-included; trace note happens inside cleaner_node

    if steps["cleaning"] and "cleaner" not in pipeline_steps_run:
        return "go_to_cleaner"
    if steps["encoding"] and "encoder" not in pipeline_steps_run:
        return "go_to_encoder"
    if steps["scaling"] and "scaler" not in pipeline_steps_run:
        return "go_to_scaler"
    if steps["imbalance_handling"] and "imbalance_handler" not in pipeline_steps_run:
        return "go_to_imbalance_handler"
    if steps["feature_selection"] and "feature_selector" not in pipeline_steps_run:
        return "go_to_feature_selector"

    return "go_to_analyst"  # all requested steps done


def critic_router(state: AgentState) -> str:
    """
    Called after the Critic node runs.

    accept / max-rounds-exceeded -> go back to orchestrator (picks next step)
    reject                       -> go back to the SAME agent that just ran
    """
    verdict = state["critic"]["current_verdict"]
    active_agent = state["metadata"]["current_active_agent"]
    total_rounds = state["critic"]["total_rounds"]
    max_rounds = state["critic"]["max_rounds"]

    if verdict is None:
        return "go_to_orchestrator"

    if verdict["verdict"] == "accept" or total_rounds >= max_rounds:
        return "go_to_orchestrator"

    # Reject -> route back to whichever agent just ran, by name
    return f"redo_{active_agent}"


# ---------------------------------------------------------
# GRAPH BUILDER
# ---------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Constructs the agent graph. Returns the compiled graph ready to invoke.
    """
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("profiler", profiler_node)
    graph.add_node("cleaner", cleaner_node)
    graph.add_node("encoder", encoder_node)
    graph.add_node("scaler", scaler_node)
    graph.add_node("imbalance_handler", imbalance_handler_node)
    graph.add_node("feature_selector", feature_selector_node)
    graph.add_node("critic", critic_node)
    graph.add_node("analyst", analyst_node)

    # Start -> Profiler always runs first
    graph.add_edge(START, "profiler")

    # Profiler -> Orchestrator decides the FIRST preprocessing step
    graph.add_conditional_edges(
        "profiler",
        orchestrator_router,
        {
            "go_to_cleaner": "cleaner",
            "go_to_encoder": "encoder",
            "go_to_scaler": "scaler",
            "go_to_imbalance_handler": "imbalance_handler",
            "go_to_feature_selector": "feature_selector",
            "go_to_analyst": "analyst",  # edge case: zero steps requested
        }
    )

    # Every preprocessing agent hands off to the SAME shared critic
    for agent_name in ["cleaner", "encoder", "scaler", "imbalance_handler", "feature_selector"]:
        graph.add_edge(agent_name, "critic")

    # Critic's verdict decides: redo same agent, or go back to orchestrator
    graph.add_conditional_edges(
        "critic",
        critic_router,
        {
            "go_to_orchestrator": "orchestrator_proxy",  # see note below
            "redo_cleaner": "cleaner",
            "redo_encoder": "encoder",
            "redo_scaler": "scaler",
            "redo_imbalance_handler": "imbalance_handler",
            "redo_feature_selector": "feature_selector",
        }
    )

    # NOTE: LangGraph conditional_edges need a NODE name on the right side,
    # not a router function directly. So "go back to orchestrator" needs a
    # tiny pass-through node that just re-runs the SAME routing decision.
    graph.add_node("orchestrator_proxy", lambda state: {})  # no-op, just a hop
    graph.add_conditional_edges(
        "orchestrator_proxy",
        orchestrator_router,
        {
            "go_to_cleaner": "cleaner",
            "go_to_encoder": "encoder",
            "go_to_scaler": "scaler",
            "go_to_imbalance_handler": "imbalance_handler",
            "go_to_feature_selector": "feature_selector",
            "go_to_analyst": "analyst",
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
    requested_steps: dict | None = None,
) -> AgentState:
    graph = build_graph()

    initial_state = make_initial_state(
        dataset_path=dataset_path,
        dataset_name=dataset_name,
        target_column=target_column,
        requested_steps=requested_steps,
    )

    print(f"\n{'='*60}")
    print(f"Starting pipeline for: {dataset_name}")
    print(f"Session: {initial_state['metadata']['session_id']}")
    print(f"{'='*60}\n")

    final_state = graph.invoke(initial_state, {"recursion_limit": 50})

    print(f"\n{'='*60}")
    print("Pipeline complete.")
    print(f"Viz events emitted: {len(final_state['visualization_events'])}")
    print(f"Errors recorded: {len(final_state['errors'])}")
    print(f"{'='*60}\n")

    return final_state


if __name__ == "__main__":
    result = run_pipeline(
        dataset_path="data/raw/sample.csv",
        dataset_name="smoke_test",
    )
    print("Final analyst summary:", result["analyst"]["analysis_summary"])
    print("Critic rounds:", result["critic"]["total_rounds"])
