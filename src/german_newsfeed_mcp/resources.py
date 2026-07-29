"""
MCP resource implementations for the ARD / Tagesschau MCP Server.

Single Responsibility: business logic for each MCP resource URI.
Plain async functions — @mcp.resource() decorators are applied in server.py.
"""
# The short "fetch channels / validate ressort" patterns are intentionally
# mirrored in tools.py — they are minimal glue, not extractable further.
# pylint: disable=duplicate-code

import logging
from typing import Optional

from ard_mcp.client import ENDPOINTS, fetch_from_api, get_news
from ard_mcp.formatters import format_channels, format_news_list
from ard_mcp.validators import VALID_REGION_IDS, validate_ressort

logger = logging.getLogger(__name__)


async def resource_homepage() -> str:
    """Return the current Tagesschau homepage news (tagesschau://homepage)."""
    logger.info("resource_homepage")
    response = await fetch_from_api(ENDPOINTS["homepage"])

    if "error" in response:
        return f"Error fetching homepage: {response['message']}"

    news_items = response.get("news", [])
    return format_news_list(news_items)


async def resource_news_by_ressort(ressort: str) -> str:
    """Return news for a category (tagesschau://news/{ressort}).

    Args:
        ressort: Category slug.
    """
    logger.info("resource_news_by_ressort ressort=%s", ressort)

    error = validate_ressort(ressort)
    if error:
        return error

    result = await get_news({"ressort": ressort})
    if "error" in result:
        return f"Error fetching news: {result['message']}"

    return format_news_list(result["items"])


async def resource_regional_news(
    region_id: str,
    ressort: Optional[str] = None,
) -> str:
    """Return regional news (tagesschau://regional/{region_id}).

    Args:
        region_id: String representation of an integer 1–16.
        ressort:   Optional category filter.
    """
    logger.info("resource_regional_news region_id=%s ressort=%s",
                region_id, ressort)

    try:
        rid = int(region_id)
    except ValueError:
        return f"Invalid region ID: {region_id!r}. Must be a number between 1 and 16."

    if rid not in VALID_REGION_IDS:
        return f"Invalid region ID: {rid}. Valid options are 1–16."

    params = {"regions": str(rid)}

    if ressort is not None:
        error = validate_ressort(ressort)
        if error:
            return error
        params["ressort"] = ressort

    result = await get_news(params)
    if "error" in result:
        return f"Error fetching regional news: {result['message']}"

    return format_news_list(result["items"])


async def resource_search(
    search_text: str,
    page_size: Optional[int] = None,
    result_page: Optional[int] = None,
) -> str:
    """Return search results (tagesschau://search/{search_text}).

    Args:
        search_text: The search query.
        page_size:   Optional results per page (1–30).
        result_page: Optional zero-based page number.
    """
    logger.info(
        "resource_search text=%r page_size=%s result_page=%s",
        search_text,
        page_size,
        result_page,
    )

    params = {"searchText": search_text}

    if page_size is not None:
        clamped = max(1, min(page_size, 30))
        params["pageSize"] = str(clamped)

    if result_page is not None:
        params["resultPage"] = str(result_page)

    response = await fetch_from_api(ENDPOINTS["search"], params)

    if "error" in response:
        return f"Error searching news: {response['message']}"

    search_results = response.get("searchResults", [])

    if not search_results:
        return f"No results found for search term: '{search_text}'"

    limit = page_size if page_size is not None else 10
    return format_news_list(search_results, limit)


async def resource_channels() -> str:
    """Return channel information (tagesschau://channels)."""
    logger.info("resource_channels")

    response = await fetch_from_api(ENDPOINTS["channels"])

    if "error" in response:
        return f"Error fetching channels: {response['message']}"

    channels = response.get("channels", [])
    return format_channels(channels)
