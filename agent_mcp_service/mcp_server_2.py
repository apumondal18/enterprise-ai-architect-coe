from mcp.server.mcpserver import MCPServer
from models import UserInput

mcp = MCPServer("User Management Server")


@mcp.tool()
def register_user(user: UserInput) -> dict:
    """Register a user with name, age and city."""

    return {
        "status": "success",
        "name": user.name,
        "age": user.age,
        "city": user.city
    }


if __name__ == "__main__":
    mcp.run()