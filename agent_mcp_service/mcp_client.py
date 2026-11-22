import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Locate the server file in the same directory as this client.
SERVER_SCRIPT = Path(__file__).with_name("enterprise_mcp_server.py")


async def connect_to_server():

    if not SERVER_SCRIPT.exists():
        raise FileNotFoundError(
            f"MCP server not found: {SERVER_SCRIPT}"
        )

    # Configure how the MCP server should be launched.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)]
    )

    # Establish stdio transport connection.
    async with stdio_client(server_params) as (read, write):

        # Create an MCP session over the connection.
        async with ClientSession(read, write) as session:

            # Initialize the MCP session.
            await session.initialize()

            print("\nConnected to Enterprise MCP Server")

            # Discover available tools.
            tools_response = await session.list_tools()
            available_tools = tools_response.tools

            if not available_tools:
                print("No tools available.")
                return

            print("\nAvailable MCP Tools")

            # Display tool information and schemas.
            for index, tool in enumerate(available_tools, start=1):

                print(f"\n{index}. {tool.name}")
                print(f"Description: {tool.description}")

                print("Input Schema:")
                print(
                    json.dumps(
                        tool.input_schema,
                        indent=4
                    )
                )

            # Dynamically select a tool.
            try:
                selection = int(
                    input("\nSelect a tool number: ")
                )

                if selection < 1 or selection > len(available_tools):
                    print("Invalid tool selection.")
                    return

            except ValueError:
                print("Please enter a valid number.")
                return

            selected_tool = available_tools[selection - 1]

            print(f"\nSelected tool: {selected_tool.name}")

            # Display required arguments from the discovered schema.
            schema = selected_tool.input_schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            print("\nExpected arguments:")

            for argument_name, details in properties.items():

                required_label = (
                    "Required" if argument_name in required
                    else "Optional"
                )

                print(
                    f"- {argument_name}: "
                    f"type={details.get('type', 'see schema')}, "
                    f"{required_label}"
                )

            # Collect arguments as JSON.
            raw_arguments = input(
                "\nEnter tool arguments as JSON: "
            )

            try:
                arguments = json.loads(raw_arguments)

                if not isinstance(arguments, dict):
                    print("Arguments must be a JSON object.")
                    return

            except json.JSONDecodeError as error:
                print(f"Invalid JSON: {error}")
                return

            # Execute the dynamically selected tool.
            print("\nExecuting MCP tool...")

            result = await session.call_tool(
                selected_tool.name,
                arguments=arguments
            )

            # Process the response.
            print("\nTool Execution Result")

            if result.is_error:
                print("Tool execution failed.")

            # Display structured response, if provided.
            if result.structured_content is not None:
                print("\nStructured Content:")
                print(
                    json.dumps(
                        result.structured_content,
                        indent=4,
                        default=str
                    )
                )

            # Display text or other content blocks.
            for content in result.content:

                if content.type == "text":
                    print("\nText Content:")
                    print(content.text)

                else:
                    print(f"\nContent type: {content.type}")


async def main():
    try:
        await connect_to_server()

    except Exception as error:
        print(f"\nMCP client error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
