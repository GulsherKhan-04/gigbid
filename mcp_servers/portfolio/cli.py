"""Entry point for the published Portfolio MCP server (stdio for Claude Desktop / Cursor)."""


def main() -> None:
    from mcp_servers.portfolio.server import mcp
    mcp.run("stdio")
