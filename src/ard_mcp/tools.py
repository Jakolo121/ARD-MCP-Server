"""
MCP tool implementations for the ARD / Tagesschau MCP Server.

Single Responsibility: business logic for each MCP tool.
These are plain async functions — the @mcp.tool() decorator is applied in
server.py.  This decoupling makes the logic independently testable without
needing a running FastMCP instance.
"""

import logging
from typing import Optional

from ard_mcp.client import ENDPOINTS, fetch_from_api, get_news
from ard_mcp.formatters import _format_streams, format_channels, format_news_list
from ard_mcp.validators import VALID_REGION_IDS, VALID_RESSORTS, validate_ressort

# VALID_RESSORTS is re-exported so tests can import it from ard_mcp.tools
__all__ = ["VALID_RESSORTS", "VALID_REGION_IDS", "validate_ressort"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def tool_get_latest_news(limit: int = 10) -> str:
    """Return the latest headlines from the Tagesschau homepage."""
    logger.info("tool_get_latest_news limit=%d", limit)
    response = await fetch_from_api(ENDPOINTS["homepage"])

    if "error" in response:
        return f"Error fetching news: {response['message']}"

    news_items = response.get("news", [])
    return format_news_list(news_items, limit)


async def tool_get_news_by_ressort(ressort: str, limit: int = 10) -> str:
    """Return news filtered by category (Ressort).

    Args:
        ressort: One of inland | ausland | wirtschaft | sport |
                 video | investigativ | wissen.
        limit:   Maximum number of items (default 10).
    """
    logger.info("tool_get_news_by_ressort ressort=%s limit=%d", ressort, limit)

    error = validate_ressort(ressort)
    if error:
        return error

    result = await get_news({"ressort": ressort}, limit)
    if "error" in result:
        return f"Error fetching news: {result['message']}"

    if not result["items"]:
        return f"No news items found for ressort '{ressort}'."

    return format_news_list(result["items"], limit)


async def tool_get_regional_news(
    region_id: int,
    ressort: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Return news for a specific German federal state.

    Args:
        region_id: 1–16 (1=Baden-Württemberg … 16=Thüringen).
        ressort:   Optional category filter.
        limit:     Maximum number of items (default 10).
    """
    logger.info(
        "tool_get_regional_news region_id=%d ressort=%s limit=%d",
        region_id,
        ressort,
        limit,
    )

    if region_id not in VALID_REGION_IDS:
        return f"Invalid region ID: {region_id}. Valid options are 1–16."

    params = {"regions": str(region_id)}

    if ressort is not None:
        error = validate_ressort(ressort)
        if error:
            return error
        params["ressort"] = ressort

    result = await get_news(params, limit)
    if "error" in result:
        return f"Error fetching regional news: {result['message']}"

    if not result["items"]:
        return f"No regional news items found for region {region_id}."

    return format_news_list(result["items"], limit)


async def tool_search_news(
    search_text: str,
    page_size: int = 10,
    result_page: int = 0,
) -> str:
    """Search for news articles by keyword.

    Args:
        search_text: Search query string.
        page_size:   Results per page (1–30, default 10).
        result_page: Zero-based page number (default 0).
    """
    logger.info(
        "tool_search_news query=%r page_size=%d result_page=%d",
        search_text,
        page_size,
        result_page,
    )

    page_size = max(1, min(page_size, 30))

    response = await fetch_from_api(
        ENDPOINTS["search"],
        {
            "searchText": search_text,
            "pageSize": str(page_size),
            "resultPage": str(result_page),
        },
    )

    if "error" in response:
        return f"Error searching news: {response['message']}"

    search_results = response.get("searchResults", [])
    total = response.get("totalItemCount", 0)

    if not search_results:
        return f"No results found for search term: '{search_text}'"

    lines = [
        f"# Search Results for '{search_text}'",
        "",
        f"Found {total} results total. "
        f"Showing {min(len(search_results), page_size)} on page {result_page}.",
        # Note: The Tagesschau API returns no relevance score — results are
        # sorted by date (newest first). Semantic ranking is not supported.
        "> ℹ️ Sorted by date (newest first). The API provides no relevance score.",
        "",
    ]

    for item in search_results[:page_size]:
        title = item.get("title", "No title")
        date = item.get("date", "")
        item_type = item.get("type", "")

        lines.append(f"## {title}")
        if date:
            lines.append(f"*{date}*")
        if item_type:
            lines.append(f"Type: {item_type}")

        # Embed video stream links when available in search results
        streams = item.get("streams", {})
        if isinstance(streams, dict) and streams:
            lines.append("")
            lines.extend(_format_streams(streams))

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


async def tool_get_news(
    regions: Optional[str] = None,
    ressort: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Flexible news fetcher — region and/or category are optional.

    Args:
        regions: Region ID as string (1–16), optional.
        ressort: Category, optional.
        limit:   Maximum number of items (default 10).
    """
    logger.info(
        "tool_get_news regions=%s ressort=%s limit=%d", regions, ressort, limit
    )

    params = {}

    if regions is not None:
        try:
            region_id = int(regions)
        except ValueError:
            return f"Invalid region ID: {regions!r}. Must be a number between 1 and 16."

        if region_id not in VALID_REGION_IDS:
            return f"Invalid region ID: {region_id}. Valid options are 1–16."

        params["regions"] = regions

    if ressort is not None:
        error = validate_ressort(ressort)
        if error:
            return error
        params["ressort"] = ressort

    result = await get_news(params if params else None, limit)
    if "error" in result:
        return f"Error fetching news: {result['message']}"

    if not result["items"]:
        return "No news items found."

    return format_news_list(result["items"], limit)


async def tool_get_channels() -> str:
    """Return available Tagesschau channels and livestream information."""
    logger.info("tool_get_channels")

    response = await fetch_from_api(ENDPOINTS["channels"])

    if "error" in response:
        return f"Error fetching channels: {response['message']}"

    channels = response.get("channels", [])
    return format_channels(channels)
