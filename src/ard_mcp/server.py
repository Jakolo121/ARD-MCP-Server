"""
FastMCP server assembly for the ARD / Tagesschau MCP Server.

Single Responsibility: create the FastMCP instance, register all tools and
resources, configure logging, and expose a run() entry-point.

Nothing else lives here — logic is in tools.py / resources.py.
"""

import logging
import logging.config
from typing import Optional

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from ard_mcp import config
from ard_mcp.resources import (
    resource_channels,
    resource_homepage,
    resource_news_by_ressort,
    resource_regional_news,
    resource_search,
)
from ard_mcp.tools import (
    tool_get_channels,
    tool_get_latest_news,
    tool_get_news,
    tool_get_news_by_ressort,
    tool_get_regional_news,
    tool_search_news,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="Tagesschau News API",
)

# ---------------------------------------------------------------------------
# Register tools
# (We wrap each plain function so FastMCP gets the right docstring & sig.)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_latest_news(limit: int = 10) -> str:
    """Get the latest news from Tagesschau.

    Args:
        limit: Maximum number of news items to return (default: 10).
    """
    return await tool_get_latest_news(limit)


@mcp.tool()
async def get_news_by_ressort(ressort: str, limit: int = 10) -> str:
    """Get news by ressort/category.

    Args:
        ressort: The ressort/category to filter by.
                 Options: inland, ausland, wirtschaft, sport, video,
                          investigativ, wissen.
        limit: Maximum number of news items to return (default: 10).
    """
    return await tool_get_news_by_ressort(ressort, limit)


@mcp.tool()
async def get_regional_news(
    region_id: int,
    ressort: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Get regional news for a specific German state.

    Args:
        region_id: The ID of the region/state.
                   1=Baden-Württemberg, 2=Bayern, 3=Berlin, 4=Brandenburg,
                   5=Bremen, 6=Hamburg, 7=Hessen, 8=Mecklenburg-Vorpommern,
                   9=Niedersachsen, 10=Nordrhein-Westfalen,
                   11=Rheinland-Pfalz, 12=Saarland, 13=Sachsen,
                   14=Sachsen-Anhalt, 15=Schleswig-Holstein, 16=Thüringen.
        ressort: Optional category filter.
        limit: Maximum number of news items to return (default: 10).
    """
    return await tool_get_regional_news(region_id, ressort, limit)


@mcp.tool()
async def search_news(
    search_text: str,
    page_size: int = 10,
    result_page: int = 0,
) -> str:
    """Search for news articles by keyword.

    Args:
        search_text: The text to search for.
        page_size: Results per page (default: 10, max: 30).
        result_page: Page number for pagination (default: 0).
    """
    return await tool_search_news(search_text, page_size, result_page)


@mcp.tool()
async def get_news(
    regions: Optional[str] = None,
    ressort: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Get news with flexible parameter options.

    Args:
        regions: Optional region ID as string (1–16).
        ressort: Optional ressort/category.
        limit: Maximum number of news items to return (default: 10).
    """
    return await tool_get_news(regions, ressort, limit)


@mcp.tool()
async def get_channels() -> str:
    """Get information about available Tagesschau channels and livestreams."""
    return await tool_get_channels()


# ---------------------------------------------------------------------------
# Register resources
# ---------------------------------------------------------------------------


@mcp.resource("tagesschau://homepage")
async def homepage_resource() -> str:
    """Get the homepage content from Tagesschau."""
    return await resource_homepage()


@mcp.resource("tagesschau://news/{ressort}")
async def news_by_ressort_resource(ressort: str) -> str:
    """Get news by ressort/category."""
    return await resource_news_by_ressort(ressort)


@mcp.resource("tagesschau://regional/{region_id}")
async def regional_news_resource(region_id: str) -> str:
    """Get regional news for a specific German state."""
    return await resource_regional_news(region_id)


@mcp.resource("tagesschau://search/{search_text}")
async def search_resource(search_text: str) -> str:
    """Search for news articles by keyword."""
    return await resource_search(search_text)


@mcp.resource("tagesschau://channels")
async def channels_resource() -> str:
    """Get information about available Tagesschau channels and livestreams."""
    return await resource_channels()


# ---------------------------------------------------------------------------
# Health check — used by Docker HEALTHCHECK and k8s liveness/readiness probes
# ---------------------------------------------------------------------------


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Return 200 OK so orchestrators can verify the server is alive."""
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Start the MCP server using the transport configured via TRANSPORT env var.

    Supported transports:
        stdio           – local Claude Desktop / CLI usage (default)
        sse             – Server-Sent Events for remote / Docker deployments
        streamable_http – Streamable HTTP, stateless, endpoint: /mcp
    """
    logger.info(
        "Starting Tagesschau MCP server — transport=%s host=%s port=%d",
        config.TRANSPORT,
        config.HOST,
        config.PORT,
    )

    if config.TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    elif config.TRANSPORT == "sse":
        mcp.run(transport="sse", host=config.HOST, port=config.PORT)
    else:  # streamable_http
        mcp.run(transport="http", host=config.HOST, port=config.PORT, stateless_http=True)
