import asyncio
from mcp import Client
from mcp_server_1 import mcp


async def main():

    async with Client(mcp) as client:

        # Discover available tools
        tools = await client.list_tools()

        print("Available tools:")
        print(tools)

        # Call hello tool
        result = await client.call_tool(
            "hello",
            {"name": "Apu"}
        )

        print("Tool response:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())