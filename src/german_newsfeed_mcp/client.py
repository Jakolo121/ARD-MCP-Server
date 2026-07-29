"""
HTTP client for the upstream tagesschau.de news API.

Single Responsibility: all network I/O to the upstream API lives here.
Other modules receive a NewsApiClient instance — assembled in server.py
(composition root) — instead of touching httpx directly.

Note: upstream API terms allow max 60 requests per hour. A local token
bucket (see rate_limiter.py) guards that budget before every request.
"""

import json
import logging
from importlib import metadata
from typing import Any, Dict, Optional

import httpx

from german_newsfeed_mcp import config
from german_newsfeed_mcp.rate_limiter import TokenBucketRateLimiter

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

_REPO_URL = "https://github.com/Jakolo121/german-newsfeed-mcp"
_FALLBACK_VERSION = "0.0.0+unknown"


def _package_version() -> str:
    """Return the installed package version.

    Falls back to a placeholder when running from an uninstalled source
    tree (e.g. tests with pythonpath=src) instead of crashing on import.
    """
    try:
        return metadata.version("german-newsfeed-mcp")
    except metadata.PackageNotFoundError:
        logger.warning(
            "Package 'german-newsfeed-mcp' not installed — using fallback version %s",
            _FALLBACK_VERSION,
        )
        return _FALLBACK_VERSION


def build_user_agent(contact: Optional[str] = None) -> str:
    """Build the RFC 9110 User-Agent string for upstream requests.

    Format:
        german-newsfeed-mcp/{version} (+{repo-url}[; contact: {contact}])

    Args:
        contact: Optional contact info (e.g. an email address).
                 The whole "; contact: ..." part is omitted when unset.
    """
    contact_part = f"; contact: {contact}" if contact else ""
    return f"german-newsfeed-mcp/{_package_version()} (+{_REPO_URL}{contact_part})"


class NewsApiClient:
    """Async client for the upstream news API with local rate limiting.

    All dependencies are injected via the constructor:

    Args:
        http_client:  A configured ``httpx.AsyncClient``. Default headers —
                      including the User-Agent — are set by the composition
                      root when building the client (see server.py).
        rate_limiter: Token bucket guarding the upstream request budget.
        base_url:     Upstream base URL (default: config.API_BASE_URL).
        timeout:      Per-request timeout in seconds (default: config.API_TIMEOUT).
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        rate_limiter: TokenBucketRateLimiter,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._http = http_client
        self._rate_limiter = rate_limiter
        self._base_url = base_url if base_url is not None else config.API_BASE_URL
        self._timeout = timeout if timeout is not None else config.API_TIMEOUT

    # One return per error class keeps the error mapping flat and readable.
    # pylint: disable-next=too-many-return-statements
    async def fetch_from_api(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch data from the upstream API.

        Args:
            endpoint: The API path (e.g. "/api2u/news").
            params:   Optional query parameters.

        Returns:
            Parsed JSON response as a dict.
            On any error — including a locally exhausted rate limit — a dict
            with ``"error"`` and ``"message"`` keys is returned so callers
            can handle failures gracefully without try/except everywhere.
        """
        if not self._rate_limiter.try_acquire():
            logger.warning("Rate limit exhausted — request to %s not sent", endpoint)
            return {
                "error": "Rate limit exceeded",
                "message": (
                    f"Local rate limit of {self._rate_limiter.capacity} requests "
                    "per hour reached (configurable via RATE_LIMIT_PER_HOUR). "
                    "No request was sent upstream. Try again later."
                ),
            }

        url = f"{self._base_url}{endpoint}"
        logger.debug("GET %s params=%s", url, params)

        try:
            response = await self._http.get(url, params=params, timeout=self._timeout)
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
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Fetch news items from the /api2u/news endpoint.

        Returns a dict with keys:
            ``items``  – list of raw news dicts (may be empty)
            ``error``  – present only when the upstream returned an error
            ``message``– human-readable error description (present with ``error``)
        """
        response = await self.fetch_from_api(ENDPOINTS["news"], params)

        if "error" in response:
            return response  # propagate error dict as-is

        items = response.get("news", [])

        return {"items": items[:limit]}
