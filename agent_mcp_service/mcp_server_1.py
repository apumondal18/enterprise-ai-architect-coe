from mcp.server.mcpserver import MCPServer

mcp = MCPServer("Simple Demo Server")

@mcp.tool()
def hello(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()