"""
FastMCP server assembly for the German Newsfeed MCP Server.

Single Responsibility: composition root — create the FastMCP instance,
assemble the NewsApiClient with all its dependencies, register all tools
and resources, configure logging, and expose a run() entry-point.

Nothing else lives here — logic is in tools.py / resources.py.
"""

import logging
import logging.config
from typing import Optional

import httpx
from fastmcp import FastMCP

from german_newsfeed_mcp import config
from german_newsfeed_mcp.client import NewsApiClient, build_user_agent
from german_newsfeed_mcp.rate_limiter import TokenBucketRateLimiter
from german_newsfeed_mcp.resources import (
    resource_channels,
    resource_homepage,
    resource_news_by_ressort,
    resource_regional_news,
    resource_search,
)
from german_newsfeed_mcp.tools import (
    tool_get_channels,
    tool_get_latest_news,
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
# Composition root — assemble the API client with injected dependencies
# ---------------------------------------------------------------------------
api_client = NewsApiClient(
    http_client=httpx.AsyncClient(
        headers={"User-Agent": build_user_agent(config.USER_AGENT_CONTACT)},
    ),
    rate_limiter=TokenBucketRateLimiter(capacity=config.RATE_LIMIT_PER_HOUR),
)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="German Newsfeed MCP",
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
    return await tool_get_latest_news(api_client, limit)


@mcp.tool()
async def get_news_by_ressort(ressort: str, limit: int = 10) -> str:
    """Get news by ressort/category.

    Args:
        ressort: The ressort/category to filter by.
                 Options: inland, ausland, wirtschaft, sport, video,
                          investigativ, wissen.
        limit: Maximum number of news items to return (default: 10).
    """
    return await tool_get_news_by_ressort(api_client, ressort, limit)


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
    return await tool_get_regional_news(api_client, region_id, ressort, limit)


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
    return await tool_search_news(api_client, search_text, page_size, result_page)


@mcp.tool()
async def get_channels() -> str:
    """Get information about available Tagesschau channels and livestreams."""
    return await tool_get_channels(api_client)


# ---------------------------------------------------------------------------
# Register resources
# ---------------------------------------------------------------------------


@mcp.resource("news://tagesschau/homepage")
async def homepage_resource() -> str:
    """Get the homepage content from Tagesschau."""
    return await resource_homepage(api_client)


@mcp.resource("news://tagesschau/news/{ressort}")
async def news_by_ressort_resource(ressort: str) -> str:
    """Get news by ressort/category."""
    return await resource_news_by_ressort(api_client, ressort)


@mcp.resource("news://tagesschau/regional/{region_id}")
async def regional_news_resource(region_id: str) -> str:
    """Get regional news for a specific German state."""
    return await resource_regional_news(api_client, region_id)


@mcp.resource("news://tagesschau/search/{search_text}")
async def search_resource(search_text: str) -> str:
    """Search for news articles by keyword."""
    return await resource_search(api_client, search_text)


@mcp.resource("news://tagesschau/channels")
async def channels_resource() -> str:
    """Get information about available Tagesschau channels and livestreams."""
    return await resource_channels(api_client)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Start the MCP server using the transport configured via TRANSPORT env var.

    Supported transports:
        stdio           – local Claude Desktop / CLI usage (default)
        sse             – Server-Sent Events for remote / Docker deployments
        streamable-http – Streamable HTTP, stateless, endpoint: /mcp
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
    else:  # streamable-http
        mcp.run(transport="http", host=config.HOST, port=config.PORT, stateless_http=True)
