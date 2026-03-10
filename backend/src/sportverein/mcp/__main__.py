"""Run the Sportverein MCP server via stdio transport."""

from sportverein.mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
