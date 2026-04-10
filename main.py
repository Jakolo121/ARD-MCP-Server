"""Entry point for the ARD / Tagesschau MCP Server.

This file is intentionally thin — all logic lives under src/ard_mcp/.
Run with:
    uv run main.py                   # stdio (default)
    TRANSPORT=sse uv run main.py     # SSE / remote
"""

from ard_mcp.server import run

if __name__ == "__main__":
    run()
