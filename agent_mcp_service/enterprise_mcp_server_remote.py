import os
import logging

from typing import Annotated, Literal, Any

from pydantic import Field
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError


# --------------------------------------------------
# 1. SERVER CONFIGURATION
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("enterprise_mcp")

mcp = MCPServer("Enterprise MCP Server")


# --------------------------------------------------
# 2. DEMO AUTHORIZATION CONFIGURATION
# --------------------------------------------------

# In this exercise, permissions are configured on
# the server side, not supplied by the MCP client.

GRANTED_SCOPES = set(
    scope.strip()
    for scope in os.getenv(
        "DEMO_GRANTED_SCOPES",
        "cloud:read,database:read,logs:read"
    ).split(",")
    if scope.strip()
)


def require_scope(required_scope: str):

    if required_scope not in GRANTED_SCOPES:

        logger.warning(
            "Authorization denied. Required scope: %s",
            required_scope
        )

        raise ToolError(
            f"Access denied. Required permission: {required_scope}"
        )


# --------------------------------------------------
# 3. SIMULATED ENTERPRISE DATA
# --------------------------------------------------

CLOUD_RESOURCES = [
    {
        "resource_id": "ec2-prod-001",
        "provider": "aws",
        "environment": "prod",
        "resource_type": "compute",
        "status": "healthy",
        "cpu_usage": 45
    },
    {
        "resource_id": "rds-prod-001",
        "provider": "aws",
        "environment": "prod",
        "resource_type": "database",
        "status": "degraded",
        "cpu_usage": 89
    },
    {
        "resource_id": "vm-dev-001",
        "provider": "azure",
        "environment": "dev",
        "resource_type": "compute",
        "status": "healthy",
        "cpu_usage": 30
    }
]


EMPLOYEE_RECORDS = [
    {
        "employee_id": 101,
        "name": "John",
        "department": "Engineering",
        "status": "active"
    },
    {
        "employee_id": 102,
        "name": "Sarah",
        "department": "Finance",
        "status": "active"
    },
    {
        "employee_id": 103,
        "name": "David",
        "department": "Engineering",
        "status": "inactive"
    }
]


SERVICE_INVENTORY = [
    {
        "service_id": "SVC-001",
        "service_name": "Payment API",
        "department": "Engineering",
        "status": "active"
    },
    {
        "service_id": "SVC-002",
        "service_name": "Reporting API",
        "department": "Finance",
        "status": "active"
    }
]


DEPLOYMENT_LOGS = [
    {
        "deployment_id": "DEP-1001",
        "level": "INFO",
        "message": "Deployment started"
    },
    {
        "deployment_id": "DEP-1001",
        "level": "INFO",
        "message": "Container image pulled"
    },
    {
        "deployment_id": "DEP-1001",
        "level": "ERROR",
        "message": "Health check failed"
    },
    {
        "deployment_id": "DEP-1002",
        "level": "INFO",
        "message": "Deployment completed successfully"
    }
]


# --------------------------------------------------
# 4. TOOL 1: CLOUD HEALTH
# --------------------------------------------------

@mcp.tool()
def query_cloud_health(
    provider: Literal["aws", "azure"],
    environment: Literal["dev", "staging", "prod"],
    resource_type: Literal[
        "compute", "database"
    ] | None = None
) -> dict[str, Any]:
    """
    Check the health of cloud resources.

    Supports AWS and Azure environments.
    Returns resource status and CPU utilization.
    """

    require_scope("cloud:read")

    resources = [
        resource
        for resource in CLOUD_RESOURCES
        if resource["provider"] == provider
        and resource["environment"] == environment
    ]

    if resource_type:
        resources = [
            resource
            for resource in resources
            if resource["resource_type"] == resource_type
        ]

    return {
        "provider": provider,
        "environment": environment,
        "total_resources": len(resources),
        "resources": resources
    }


# --------------------------------------------------
# 5. TOOL 2: DATABASE LOOKUP
# --------------------------------------------------

@mcp.tool()
def execute_database_lookup(
    table: Literal["employees", "service_inventory"],
    department: Annotated[
        str | None,
        Field(min_length=2, max_length=50)
    ] = None,
    status: Literal["active", "inactive"] | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10
) -> dict[str, Any]:
    """
    Perform a read-only lookup against enterprise
    employee or service inventory records.

    Only approved tables and filters are supported.
    """

    require_scope("database:read")

    # Explicit table allowlist
    if table == "employees":
        records = EMPLOYEE_RECORDS

    elif table == "service_inventory":
        records = SERVICE_INVENTORY

    else:
        raise ToolError("Unsupported database table.")

    results = records

    if department:
        results = [
            record
            for record in results
            if record["department"].lower()
            == department.strip().lower()
        ]

    if status:
        results = [
            record
            for record in results
            if record["status"] == status
        ]

    results = results[:limit]

    return {
        "table": table,
        "records_found": len(results),
        "read_only": True,
        "results": results
    }


# --------------------------------------------------
# 6. TOOL 3: DEPLOYMENT LOG INSPECTION
# --------------------------------------------------

@mcp.tool()
def inspect_deployment_logs(
    deployment_id: Annotated[
        str,
        Field(pattern=r"^DEP-\d{4,8}$")
    ],
    level: Literal[
        "INFO", "WARNING", "ERROR", "ALL"
    ] = "ALL",
    limit: Annotated[int, Field(ge=1, le=100)] = 20
) -> dict[str, Any]:
    """
    Retrieve deployment logs for a specific deployment.

    Supports INFO, WARNING, ERROR and ALL log levels.
    """

    require_scope("logs:read")

    logs = [
        log
        for log in DEPLOYMENT_LOGS
        if log["deployment_id"] == deployment_id
    ]

    if level != "ALL":
        logs = [
            log
            for log in logs
            if log["level"] == level
        ]

    logs = logs[:limit]

    return {
        "deployment_id": deployment_id,
        "level": level,
        "total_logs": len(logs),
        "logs": logs
    }


# --------------------------------------------------
# 7. SERVER EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    logger.info("Starting Enterprise MCP Server")

    mcp.run()
