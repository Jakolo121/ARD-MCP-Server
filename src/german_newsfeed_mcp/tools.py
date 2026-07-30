"""
MCP tool implementations for the German Newsfeed MCP Server.

Single Responsibility: business logic for each MCP tool.
These are plain async functions — the @mcp.tool() decorator is applied in
server.py.  This decoupling makes the logic independently testable without
needing a running FastMCP instance.

Each function receives the NewsApiClient as its first argument — injected
by the composition root in server.py.
"""

import logging
from typing import Optional

from german_newsfeed_mcp.client import ENDPOINTS, NewsApiClient
from german_newsfeed_mcp.formatters import _format_streams, format_channels, format_news_list
from german_newsfeed_mcp.validators import VALID_REGION_IDS, VALID_RESSORTS, normalise_ressort, validate_ressort

# VALID_RESSORTS is re-exported so tests can import it from german_newsfeed_mcp.tools
__all__ = ["VALID_RESSORTS", "VALID_REGION_IDS", "validate_ressort"]

logger = logging.getLogger(__name__)

# The Tagesschau /api2u/news endpoint returns at most this many items per call.
_API_MAX_NEWS_ITEMS = 50

# Advisory notice prepended when both regions AND ressort are requested.
# Verified 2025-04: the upstream API silently ignores `regions` when `ressort`
# is present — only ressort-filtered results are returned.
_REGION_RESSORT_WARNING = (
    "> ⚠️ **API limitation:** The Tagesschau API does not support filtering by "
    "both region and ressort simultaneously. The `regions` parameter is silently "
    "ignored by the upstream API when `ressort` is set. "
    "Showing results filtered by **ressort only**.\n\n"
)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def tool_get_latest_news(api: NewsApiClient, limit: int = 10) -> str:
    """Return the latest headlines from the Tagesschau homepage.

    Args:
        api:   Injected client for upstream API access.
        limit: Maximum number of items (default 10).
    """
    logger.info("tool_get_latest_news limit=%d", limit)

    if limit <= 0:
        return "ℹ️ limit=0 — no items requested. Please specify a limit ≥ 1."

    response = await api.fetch_from_api(ENDPOINTS["homepage"])

    if "error" in response:
        return f"Error fetching news: {response['message']}"

    news_items = response.get("news", [])
    result = format_news_list(news_items, limit)

    if limit > _API_MAX_NEWS_ITEMS:
        result += (
            f"\n\n>Requested limit {limit} exceeds the API maximum of"
            f" {_API_MAX_NEWS_ITEMS} items per request."
        )

    return result


async def tool_get_news_by_ressort(
    api: NewsApiClient,
    ressort: str,
    limit: int = 10,
) -> str:
    """Return news filtered by category (Ressort).

    Args:
        api:     Injected client for upstream API access.
        ressort: One of inland | ausland | wirtschaft | sport |
                 video | investigativ | wissen.
        limit:   Maximum number of items (default 10).
    """
    logger.info("tool_get_news_by_ressort ressort=%s limit=%d", ressort, limit)

    if limit <= 0:
        return "ℹ️ limit=0 — no items requested. Please specify a limit ≥ 1."

    ressort = normalise_ressort(ressort)
    error = validate_ressort(ressort)
    if error:
        return error

    result = await api.get_news({"ressort": ressort}, limit)
    if "error" in result:
        return f"Error fetching news: {result['message']}"

    if not result["items"]:
        return f"No news items found for ressort '{ressort}'."

    formatted = format_news_list(result["items"], limit)

    if limit > _API_MAX_NEWS_ITEMS:
        formatted += (
            f"\n\n>Requested limit {limit} exceeds the API maximum of"
            f" {_API_MAX_NEWS_ITEMS} items per request."
        )

    return formatted


async def tool_get_regional_news(
    api: NewsApiClient,
    region_id: int,
    ressort: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Return news for a specific German federal state.

    Args:
        api:       Injected client for upstream API access.
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

    if limit <= 0:
        return "ℹ️ limit=0 — no items requested. Please specify a limit ≥ 1."

    if region_id not in VALID_REGION_IDS:
        return f"Invalid region ID: {region_id}. Valid options are 1–16."

    params = {"regions": str(region_id)}

    if ressort is not None:
        ressort = normalise_ressort(ressort)
        error = validate_ressort(ressort)
        if error:
            return error
        params["ressort"] = ressort

    result = await api.get_news(params, limit)
    if "error" in result:
        return f"Error fetching regional news: {result['message']}"

    if not result["items"]:
        return f"No regional news items found for region {region_id}."

    formatted = format_news_list(result["items"], limit)

    if ressort is not None:
        formatted = _REGION_RESSORT_WARNING + formatted

    if limit > _API_MAX_NEWS_ITEMS:
        formatted += (
            f"\n\n>Requested limit {limit} exceeds the API maximum of"
            f" {_API_MAX_NEWS_ITEMS} items per request."
        )

    return formatted


async def tool_search_news(
    api: NewsApiClient,
    search_text: str,
    page_size: int = 10,
    result_page: int = 0,
) -> str:
    """Search for news articles by keyword.

    Args:
        api:         Injected client for upstream API access.
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

    response = await api.fetch_from_api(
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


async def tool_get_channels(api: NewsApiClient) -> str:
    """Return available Tagesschau channels and livestream information.

    Args:
        api: Injected client for upstream API access.
    """
    logger.info("tool_get_channels")

    response = await api.fetch_from_api(ENDPOINTS["channels"])

    if "error" in response:
        return f"Error fetching channels: {response['message']}"

    channels = response.get("channels", [])
    return format_channels(channels)
