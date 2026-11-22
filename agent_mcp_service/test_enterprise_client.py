import asyncio

import enterprise_mcp_server as server

from mcp import Client


async def main():

    async with Client(server.mcp) as client:

        # --------------------------------
        # 1. DISCOVER REGISTERED TOOLS
        # --------------------------------

        print("\n========== TOOL DISCOVERY ==========")

        tools = await client.list_tools()

        for tool in tools.tools:

            print("\nTool:", tool.name)
            print("Description:", tool.description)
            print("Input Schema:", tool.input_schema)

        # --------------------------------
        # 2. CLOUD HEALTH
        # --------------------------------

        print("\n========== CLOUD HEALTH ==========")

        cloud_result = await client.call_tool(
            "query_cloud_health",
            {
                "provider": "aws",
                "environment": "prod"
            }
        )

        print(cloud_result.structured_content)

        # --------------------------------
        # 3. DATABASE LOOKUP
        # --------------------------------

        print("\n========== DATABASE LOOKUP ==========")

        db_result = await client.call_tool(
            "execute_database_lookup",
            {
                "table": "employees",
                "department": "Engineering",
                "status": "active",
                "limit": 10
            }
        )

        print(db_result.structured_content)

        # --------------------------------
        # 4. DEPLOYMENT LOGS
        # --------------------------------

        print("\n========== DEPLOYMENT LOGS ==========")

        log_result = await client.call_tool(
            "inspect_deployment_logs",
            {
                "deployment_id": "DEP-1001",
                "level": "ERROR",
                "limit": 20
            }
        )

        print(log_result.structured_content)

        # --------------------------------
        # 5. VALIDATION FAILURE
        # --------------------------------

        print("\n========== VALIDATION TEST ==========")

        invalid_result = await client.call_tool(
            "query_cloud_health",
            {
                "provider": "google",
                "environment": "prod"
            }
        )

        print("Is Error:", invalid_result.is_error)
        print("Error:", invalid_result.content)

        # --------------------------------
        # 6. AUTHORIZATION FAILURE
        # --------------------------------

        print("\n========== AUTHORIZATION TEST ==========")

        # Temporarily remove database permission
        original_scopes = server.GRANTED_SCOPES.copy()

        server.GRANTED_SCOPES.remove("database:read")

        denied_result = await client.call_tool(
            "execute_database_lookup",
            {
                "table": "employees"
            }
        )

        print("Is Error:", denied_result.is_error)
        print("Error:", denied_result.content)

        # Restore permissions
        server.GRANTED_SCOPES = original_scopes


if __name__ == "__main__":
    asyncio.run(main())
