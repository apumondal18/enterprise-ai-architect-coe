from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy, Command
from langgraph.errors import NodeError
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import asyncio

# 1. Shared graph state
class GraphState(TypedDict):
    task: str
    next_nodes: list[str]
    results: Annotated[list, operator.add]
    final_report: str


# 2. Supervisor
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


# 3. Infrastructure worker
def infrastructure_worker(state: GraphState):

    print("\nInfrastructure Worker executing...")

    return {
        "results": [{
            "worker": "infrastructure",
            "status": "success",
            "finding": "CPU utilization is 85%. Memory utilization is 72%."
        }]
    }


# 4. Deployment worker
def deployment_worker(state: GraphState):

    print("\nDeployment Worker executing...")

    return {
        "results": [{
            "worker": "deployment",
            "status": "success",
            "finding": "Deployment failed at 10:30. Application restart detected."
        }]
    }


# 5. Database worker
'''
def database_worker(state: GraphState):

    print("\nDatabase Worker executing...")

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        try:
            print(f"Database attempt {attempt}/{max_attempts}")

            # Simulate a database operation
            raise ConnectionError("Database connection timed out")

            # In a real implementation, the database call
            # would happen here.

        except ConnectionError as exc:

            print(f"Attempt {attempt} failed: {exc}")

            if attempt == max_attempts:

                print("All attempts exhausted.")

                return {
                    "results": [{
                        "worker": "database",
                        "status": "unavailable",
                        "finding": (
                            f"Database unavailable after "
                            f"{max_attempts} attempts: {exc}"
                        )
                    }]
                }

    return {
        "results": [{
            "worker": "database",
            "status": "success",
            "finding": "Database check completed successfully."
        }]
    }

'''
def database_worker(state: GraphState):

    print("\nDatabase Worker executing...")

    raise ConnectionError(
        "Database connection timed out"
    )

'''    return {
        "results": [{
            "worker": "database",
            "finding": "Database connection timeout detected."
        }]
    }
'''

# Database error handler
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
                    f"Database operation failed after retries: "
                    f"{error.error}"
                )
            }]
        },
        goto="database_recovery_complete"
    )

# 6. Conditional routing
def route_task(state: GraphState):

    if not state["next_nodes"]:
        return END

    return state["next_nodes"]


# 7. Aggregator

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
        f"PRODUCTION HEALTH ASSESSMENT\n"
        f"Overall Status: {overall_status}\n\n"
        + "\n".join(report_lines)
    )

    return {
        "final_report": final_report
    }

'''
def aggregator(state: GraphState):

    print("\nAggregator executing...")

    # Index findings by worker identity
    findings = {
        item["worker"]: item["finding"]
        for item in state["results"]
    }

    # Present results in a deliberate business order
    ordered_workers = [
        "infrastructure",
        "deployment",
        "database"
    ]

    report_lines = []

    for worker in ordered_workers:
        if worker in findings:
            report_lines.append(
                f"{worker.upper()}: {findings[worker]}"
            )

    final_report = (
        "PRODUCTION HEALTH ASSESSMENT\n\n"
        + "\n".join(report_lines)
    )

    return {"final_report": final_report}
'''

def database_recovery_complete(state: GraphState):
    print("Database branch completed.")
    return {}

# 8. Build graph
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


# 9. Define execution flow
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

# Fan-in: wait for all three workers
builder.add_edge(
    [
        "infrastructure_worker",
        "deployment_worker",
        "database_recovery_complete"
    ],
    "aggregator"
)

builder.add_edge("aggregator", END)



async def main():

    async with AsyncSqliteSaver.from_conn_string(
        "checkpoints.sqlite"
    ) as checkpointer:

        graph = builder.compile(
            checkpointer=checkpointer
        )

        config = {
            "configurable": {
                "thread_id": "production-001"
            }
        }

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

        

        snapshot = await graph.aget_state(config)

        print("\nCheckpoint State:")
        print(snapshot.values)

        print("\nCheckpoint Config:")
        print(snapshot.config)

    
    print("\nFinal Results:")
    print(final_state["results"])

    print("\nConsolidated Report:")
    print(final_state["final_report"])


if __name__ == "__main__":
    asyncio.run(main())