"""
HTTP client for the Tagesschau API.

Single Responsibility: all network I/O to the upstream API lives here.
All other modules call fetch_from_api() or _get_news() instead of touching
httpx directly.

Note: Tagesschau API terms allow max 60 requests per hour for non-commercial use.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from ard_mcp import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API endpoint registry
# ---------------------------------------------------------------------------
ENDPOINTS: Dict[str, str] = {
    "homepage": "/api2u/homepage",
    "news": "/api2u/news",
    "channels": "/api2u/channels",
    "search": "/api2u/search",
}


async def fetch_from_api(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fetch data from the Tagesschau API.

    Args:
        endpoint: The API path (e.g. "/api2u/news").
        params:   Optional query parameters.

    Returns:
        Parsed JSON response as a dict.
        On any error a dict with ``"error"`` and ``"message"`` keys is returned
        so callers can handle failures gracefully without try/except everywhere.
    """
    url = f"{config.API_BASE_URL}{endpoint}"
    logger.debug("GET %s params=%s", url, params)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=config.API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.debug("Response %d from %s", response.status_code, url)
            return data

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP error %d from %s: %s",
            exc.response.status_code,
            url,
            exc,
        )
        return {
            "error": "HTTP error",
            "message": f"Status {exc.response.status_code} — {exc}",
        }

    except httpx.TimeoutException as exc:
        logger.warning("Timeout reaching %s: %s", url, exc)
        return {"error": "Timeout", "message": str(exc)}

    except httpx.RequestError as exc:
        logger.warning("Request error for %s: %s", url, exc)
        return {"error": "Request error", "message": str(exc)}

    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON from %s: %s", url, exc)
        return {"error": "Invalid JSON response", "message": str(exc)}

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Unexpected error for %s: %s", url, exc)
        return {"error": "Unknown error", "message": str(exc)}


async def get_news(
    params: Optional[Dict[str, Any]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Fetch news items from the /api2u/news endpoint.

    Returns a dict with keys:
        ``items``  – list of raw news dicts (may be empty)
        ``error``  – present only when the upstream returned an error
        ``message``– human-readable error description (present with ``error``)
    """
    response = await fetch_from_api(ENDPOINTS["news"], params)

    if "error" in response:
        return response  # propagate error dict as-is

    items = response.get("news", [])

    return {"items": items[:limit]}
