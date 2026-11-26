import asyncio
from mcp import Client


SERVER_URL = "http://13.221.144.96:8080/mcp"


async def main():

    print("Connecting to remote MCP server...")

    async with Client(SERVER_URL) as client:

        print("\nConnection established!")

        # Discover available tools
        tools = await client.list_tools()

        print("\nAvailable MCP tools:")

        for tool in tools.tools:
            print(f"- {tool.name}: {tool.description}")
        # Execute a tool
        print("\nCalling query_cloud_health...")

        result = await client.call_tool(
            "query_cloud_health",
            {
                "provider": "gcp",
                "environment": "dev"
            }
        )

        print("\nTool response:")
        print(result)

        result1= await client.call_tool(
            "blabla_bla",
            {}
        )

        print(result1)


if __name__ == "__main__":
    asyncio.run(main())
