import asyncio
from mcp import Client
from mcp.client.sse import sse_client

SERVER_URL = "http://54.197.36.31:8080/sse"

async def main():

    print("Connecting to legacy SSE MCP server...")

    async with Client(sse_client(SERVER_URL)) as client:

        print("MCP session established!")

        tools = await client.list_tools()

        print("\nAvailable tools:")
        for tool in tools.tools:
            print(f"- {tool.name}: {tool.description}")

        print("\nCalling cloud health tool...")

        result = await client.call_tool(
            "query_cloud_health",
            {
                "provider": "aws",
                "environment": "dev"
            }
        )

        print("\nResult:")
        print(result)

if __name__ == "__main__":
    asyncio.run(main())