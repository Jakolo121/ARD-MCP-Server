"""Entry point for the ARD / Tagesschau MCP Server.

This file is intentionally thin — all logic lives under src/ard_mcp/.
Run with:
    uv run main.py                   # stdio (default)
    TRANSPORT=streamable_http uv run main.py     # Streamable HTTP / remote
"""

from ard_mcp.server import run

if __name__ == "__main__":
    run()
