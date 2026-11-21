import asyncio
from mcp import Client
from mcp_server_2 import mcp


async def main():

    async with Client(mcp) as client:

        tools = await client.list_tools()

        for tool in tools.tools:
            print(tool.name)
            print(tool.description)
            print(tool.input_schema)

        result = await client.call_tool(
            "register_user",
            {
                "user": {
                    "name": "Apu",
                    "age": 30,
                    "city": "Bengaluru"
                }
            }
        )

        print(result)


if __name__ == "__main__":
    asyncio.run(main())