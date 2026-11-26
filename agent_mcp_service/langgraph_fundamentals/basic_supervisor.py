from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END


class GraphState(TypedDict):
    task: str
    next_nodes: list[str]
    results: Annotated[list, operator.add]


def supervisor(state: GraphState):

    task = state["task"].lower()

    print("\nSupervisor received:", task)

    selected_workers = []


    if "research" in task:
        selected_workers.append("research_worker")

    if "analyse" in task or "analyze" in task:
        selected_workers.append("analysis_worker")

    print("Selected workers:", selected_workers)

    

    return {
        "next_nodes": selected_workers
    }

def research_worker(state: GraphState):

    print("\nResearch Worker executing...")

    output = f"Research completed for: {state['task']}"

    return {
        "results": [output]
    }

def analysis_worker(state: GraphState):
    print("\nAnalysis Worker executing...")
    output = f"Analysis completed for: {state['task']}"
    return {
        "results": [output]
    }

def route_task(state: GraphState):

    if not state["next_nodes"]:
        return END

    return state["next_nodes"]
    

builder = StateGraph(GraphState)

# Register nodes
builder.add_node("supervisor", supervisor)

builder.add_node(
    "research_worker",
    research_worker
)

builder.add_node(
    "analysis_worker",
    analysis_worker
)

# Define entry point
builder.add_edge(START, "supervisor")

# Define conditional routing
builder.add_conditional_edges(
    "supervisor",
    route_task
)

# Define worker termination
builder.add_edge("research_worker", END)

builder.add_edge("analysis_worker", END)

# Compile graph
graph = builder.compile()


if __name__ == "__main__":

    initial_state = {
        "task": "Analyse & Research artificial intelligence",
        "next_nodes": "",
        "results": []
    }

    final_state = graph.invoke(initial_state)

    print("\nFinal State:")
    print(final_state)