"""Entry point for the ARD / Tagesschau MCP Server.

This file is intentionally thin — all logic lives under src/german_newsfeed_mcp/.
Run with:
    uv run main.py                   # stdio (default)
    TRANSPORT=streamable_http uv run main.py     # Streamable HTTP / remote
"""

from german_newsfeed_mcp.server import run

if __name__ == "__main__":
    run()
