
from typing import TypedDict, Annotated
import operator
import asyncio

from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy, Command
from langgraph.errors import NodeError

# Import MCP client helper from parent directory

from test_script import call_mcp_tool


# ============================================================
# 1. SHARED GRAPH STATE
# ============================================================

class GraphState(TypedDict):
    task: str
    next_nodes: list[str]
    results: Annotated[list, operator.add]
    final_report: str


# ============================================================
# 2. SUPERVISOR
# ============================================================

def supervisor(state: GraphState):

    task = state["task"].lower()

    print("\nSupervisor received:", task)

    selected_workers = []

    if "production" in task or "health" in task:
        selected_workers.append("infrastructure_worker")

    if "deployment" in task or "logs" in task:
        selected_workers.append("deployment_worker")

    if "database" in task or "db" in task:
        selected_workers.append("database_worker")

    print("Selected workers:", selected_workers)

    return {"next_nodes": selected_workers}


# ============================================================
# 3. INFRASTRUCTURE WORKER - REAL MCP INTEGRATION
# ============================================================

async def infrastructure_worker(state: GraphState):

    print("\nInfrastructure Worker: Calling MCP tool...")

    cloud_health = await call_mcp_tool(
        "query_cloud_health",
        {
            "provider": "aws",
            "environment": "prod",
            "resource_type": "compute"
        }
    )

    print("Infrastructure Worker: MCP result received")

    return {
        "results": [{
            "worker": "infrastructure",
            "status": "success",
            "finding": cloud_health
        }]
    }


# ============================================================
# 4. DEPLOYMENT WORKER - CURRENTLY SIMULATED
# ============================================================

def deployment_worker(state: GraphState):

    print("\nDeployment Worker executing...")

    return {
        "results": [{
            "worker": "deployment",
            "status": "success",
            "finding": (
                "Deployment failed at 10:30. "
                "Application restart detected."
            )
        }]
    }


# ============================================================
# 5. DATABASE WORKER - RETRY TEST
# ============================================================

def database_worker(state: GraphState):

    print("\nDatabase Worker executing...")

    raise ConnectionError(
        "Database connection timed out"
    )


# ============================================================
# 6. DATABASE ERROR HANDLER
# ============================================================

def database_error_handler(
    state: GraphState,
    error: NodeError
):

    print("\nDatabase error handler executing...")
    print(f"Failed node: {error.node}")
    print(f"Exception: {error.error}")

    return Command(
        update={
            "results": [{
                "worker": "database",
                "status": "unavailable",
                "finding": (
                    "Database operation failed after retries: "
                    f"{error.error}"
                )
            }]
        },
        goto="database_recovery_complete"
    )


# ============================================================
# 7. CONDITIONAL ROUTING
# ============================================================

def route_task(state: GraphState):

    if not state["next_nodes"]:
        return END

    return state["next_nodes"]


# ============================================================
# 8. DATABASE RECOVERY COMPLETION NODE
# ============================================================

def database_recovery_complete(state: GraphState):

    print("\nDatabase branch completed.")

    return {}


# ============================================================
# 9. AGGREGATOR
# ============================================================

def aggregator(state: GraphState):

    print("\nAggregator executing...")

    findings = {
        item["worker"]: item
        for item in state["results"]
    }

    ordered_workers = [
        "infrastructure",
        "deployment",
        "database"
    ]

    report_lines = []

    unavailable_workers = []

    for worker in ordered_workers:

        if worker not in findings:

            report_lines.append(
                f"{worker.upper()}: NO RESULT RECEIVED"
            )

            unavailable_workers.append(worker)

            continue

        result = findings[worker]

        report_lines.append(
            f"{worker.upper()}: {result['finding']}"
        )

        if result["status"] != "success":
            unavailable_workers.append(worker)

    if unavailable_workers:
        overall_status = "PARTIALLY ASSESSED"
    else:
        overall_status = "ASSESSMENT COMPLETED"

    final_report = (
        "PRODUCTION HEALTH ASSESSMENT\n"
        f"Overall Status: {overall_status}\n\n"
        + "\n".join(report_lines)
    )

    return {
        "final_report": final_report
    }


# ============================================================
# 10. BUILD GRAPH
# ============================================================

builder = StateGraph(GraphState)

builder.add_node("supervisor", supervisor)

builder.add_node(
    "infrastructure_worker",
    infrastructure_worker
)

builder.add_node(
    "deployment_worker",
    deployment_worker
)

builder.add_node(
    "database_worker",
    database_worker,
    retry_policy=RetryPolicy(max_attempts=3),
    error_handler=database_error_handler
)

builder.add_node(
    "database_recovery_complete",
    database_recovery_complete
)

builder.add_node("aggregator", aggregator)


# ============================================================
# 11. DEFINE EXECUTION FLOW
# ============================================================

builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_task
)

# Successful database execution
builder.add_edge(
    "database_worker",
    "database_recovery_complete"
)

# Fan-in: wait for all three branches
builder.add_edge(
    [
        "infrastructure_worker",
        "deployment_worker",
        "database_recovery_complete"
    ],
    "aggregator"
)

builder.add_edge("aggregator", END)


# ============================================================
# 12. COMPILE GRAPH
# ============================================================

graph = builder.compile()


# ============================================================
# 13. ASYNC EXECUTION
# ============================================================

async def main():

    initial_state = {
        "task": (
            "Check production application health, "
            "inspect deployment logs, "
            "and identify database issues"
        ),
        "next_nodes": [],
        "results": [],
        "final_report": ""
    }

    # IMPORTANT: Use ainvoke because infrastructure_worker is async
    final_state = await graph.ainvoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    for result in final_state["results"]:
        print(f"\nWorker: {result['worker']}")
        print(f"Status: {result['status']}")
        print(f"Finding: {result['finding']}")

    print("\n" + "=" * 60)
    print("CONSOLIDATED REPORT")
    print("=" * 60)

    print(final_state["final_report"])


if __name__ == "__main__":
    asyncio.run(main())
