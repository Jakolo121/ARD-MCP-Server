"""
Tests for german_newsfeed_mcp.client — HTTP client layer.

Section A: Unit tests using unittest.mock (no network I/O).
Section B: Integration tests against the real Tagesschau API.
           These are marked with @pytest.mark.integration and require
           an internet connection.  Run them explicitly with:
               uv run pytest -m integration
"""

import importlib
import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from german_newsfeed_mcp import config
from german_newsfeed_mcp.client import ENDPOINTS, NewsApiClient, build_user_agent
from german_newsfeed_mcp.rate_limiter import TokenBucketRateLimiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(payload=None, status_code=200):
    """Build a MagicMock mimicking an httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else {}
    response.raise_for_status = MagicMock()
    return response


def _make_api(http_client, limiter=None):
    """NewsApiClient with a generous default limiter (not under test here)."""
    return NewsApiClient(
        http_client=http_client,
        rate_limiter=limiter or TokenBucketRateLimiter(capacity=1000),
    )


# ===========================================================================
# Section A — Unit / mock tests
# ===========================================================================


class TestBuildUserAgent:
    """Unit tests for the RFC 9110 User-Agent string."""

    def test_format_without_contact(self):
        """Without contact, the UA must be product/version (+repo-url)."""
        ua = build_user_agent()
        assert re.fullmatch(
            r"german-newsfeed-mcp/\S+ "
            r"\(\+https://github\.com/Jakolo121/german-newsfeed-mcp\)",
            ua,
        ), f"unexpected UA format: {ua!r}"

    def test_format_with_contact(self):
        """With contact, '; contact: ...' must appear inside the comment."""
        ua = build_user_agent("maintainer@example.org")
        assert re.fullmatch(
            r"german-newsfeed-mcp/\S+ "
            r"\(\+https://github\.com/Jakolo121/german-newsfeed-mcp; "
            r"contact: maintainer@example\.org\)",
            ua,
        ), f"unexpected UA format: {ua!r}"

    def test_empty_contact_is_omitted(self):
        """An empty contact string must behave like no contact at all."""
        assert build_user_agent("") == build_user_agent()

    def test_no_browser_or_app_impersonation(self):
        """The UA must not imitate a browser or app user agent."""
        ua = build_user_agent().lower()
        for token in ("mozilla", "chrome", "safari", "dalvik", "okhttp"):
            assert token not in ua

    def test_contact_env_reaches_config(self, monkeypatch):
        """USER_AGENT_CONTACT env var must land in config.USER_AGENT_CONTACT."""
        monkeypatch.setenv("USER_AGENT_CONTACT", "ops@example.org")
        try:
            cfg = importlib.reload(config)
            assert cfg.USER_AGENT_CONTACT == "ops@example.org"
        finally:
            monkeypatch.undo()
            importlib.reload(config)

    def test_unset_contact_env_is_none(self, monkeypatch):
        """Without USER_AGENT_CONTACT env var, config must hold None."""
        monkeypatch.delenv("USER_AGENT_CONTACT", raising=False)
        try:
            cfg = importlib.reload(config)
            assert cfg.USER_AGENT_CONTACT is None
        finally:
            monkeypatch.undo()
            importlib.reload(config)


class TestFetchFromApiMock:
    """Unit tests for NewsApiClient.fetch_from_api using a mocked http client."""

    async def test_successful_response_returns_json(self):
        """A 200 response must be parsed and returned as a dict."""
        http = AsyncMock()
        http.get = AsyncMock(
            return_value=_mock_response({"news": [], "type": "news"})
        )
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert "news" in result
        assert result["type"] == "news"

    async def test_http_status_error_returns_error_dict(self):
        """An HTTP error status must be returned as an error dict."""
        error_response = MagicMock()
        error_response.status_code = 503

        http = AsyncMock()
        http.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "503", request=MagicMock(), response=error_response
            )
        )
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert "error" in result
        assert "message" in result

    async def test_timeout_returns_error_dict(self):
        """A timeout must be returned as an error dict with error='Timeout'."""
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Timeout"

    async def test_request_error_returns_error_dict(self):
        """A network request error must be returned as an error dict."""
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Request error"

    async def test_json_decode_error_returns_error_dict(self):
        """A malformed JSON body must be returned as an error dict."""
        response = _mock_response()
        response.json.side_effect = json.JSONDecodeError("bad json", "", 0)

        http = AsyncMock()
        http.get = AsyncMock(return_value=response)
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Invalid JSON response"

    async def test_unexpected_exception_returns_error_dict(self):
        """Any unexpected exception must be caught and returned as an error dict."""
        http = AsyncMock()
        http.get = AsyncMock(side_effect=RuntimeError("unexpected!"))
        api = _make_api(http)

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Unknown error"

    async def test_params_are_forwarded(self):
        """Query parameters must be forwarded to the http client."""
        http = AsyncMock()
        http.get = AsyncMock(
            return_value=_mock_response({"news": [], "regional": []})
        )
        api = _make_api(http)

        await api.fetch_from_api(ENDPOINTS["news"], {"ressort": "inland"})

        call_kwargs = http.get.call_args
        assert call_kwargs.kwargs["params"] == {"ressort": "inland"}

    async def test_injected_base_url_is_used(self):
        """The injected base_url must be used to build the request URL."""
        http = AsyncMock()
        http.get = AsyncMock(return_value=_mock_response({"news": []}))
        api = NewsApiClient(
            http_client=http,
            rate_limiter=TokenBucketRateLimiter(capacity=10),
            base_url="https://example.org",
        )

        await api.fetch_from_api(ENDPOINTS["news"])

        assert http.get.call_args.args[0] == "https://example.org/api2u/news"


class TestRateLimiting:
    """Unit tests for the injected rate limiter in NewsApiClient."""

    async def test_61st_call_within_hour_is_rejected(self):
        """With a 60/h limit, the 61st call in a frozen hour must fail —
        and must never reach the network."""
        limiter = TokenBucketRateLimiter(capacity=60, clock=lambda: 0.0)
        http = AsyncMock()
        http.get = AsyncMock(return_value=_mock_response({"news": []}))
        api = _make_api(http, limiter=limiter)

        for i in range(60):
            result = await api.fetch_from_api(ENDPOINTS["news"])
            assert "error" not in result, f"call {i + 1} unexpectedly failed"

        result = await api.fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Rate limit exceeded"
        assert "RATE_LIMIT_PER_HOUR" in result["message"]
        assert http.get.await_count == 60  # the 61st call was never sent

    async def test_request_allowed_again_after_refill(self):
        """After the bucket refills one token, requests must succeed again."""
        now = {"t": 0.0}
        limiter = TokenBucketRateLimiter(capacity=60, clock=lambda: now["t"])
        http = AsyncMock()
        http.get = AsyncMock(return_value=_mock_response({"news": []}))
        api = _make_api(http, limiter=limiter)

        for _ in range(60):
            await api.fetch_from_api(ENDPOINTS["news"])
        assert (await api.fetch_from_api(ENDPOINTS["news"])).get("error")

        now["t"] += 61.0  # > 60 s → one token refilled at 60/h

        result = await api.fetch_from_api(ENDPOINTS["news"])
        assert "error" not in result


class TestGetNewsMock:
    """Unit tests for the get_news() convenience method."""

    async def test_returns_news_key_by_default(self):
        """Without filters, get_news must return items from the 'news' key."""
        payload = {"news": [{"title": "Foo"}], "regional": [{"title": "Bar"}]}
        api = _make_api(AsyncMock())
        with patch.object(api, "fetch_from_api", AsyncMock(return_value=payload)):
            result = await api.get_news()
        assert result["items"] == [{"title": "Foo"}]

    async def test_returns_news_key_when_regions_param_given(self):
        """Region-filtered results must still be taken from the 'news' key."""
        # The Tagesschau API always returns region-filtered results under the
        # "news" key; the "regional" key is always empty for this endpoint.
        payload = {"news": [{"title": "Bayern News"}], "regional": []}
        api = _make_api(AsyncMock())
        with patch.object(api, "fetch_from_api", AsyncMock(return_value=payload)):
            result = await api.get_news(params={"regions": "2"})
        assert result["items"] == [{"title": "Bayern News"}]

    async def test_limit_is_applied(self):
        """The limit parameter must slice the returned items list."""
        items = [{"title": f"Item {i}"} for i in range(20)]
        payload = {"news": items, "regional": []}
        api = _make_api(AsyncMock())
        with patch.object(api, "fetch_from_api", AsyncMock(return_value=payload)):
            result = await api.get_news(limit=5)
        assert len(result["items"]) == 5

    async def test_propagates_error_response(self, error_response):
        """An error response from the API must be forwarded unchanged."""
        api = _make_api(AsyncMock())
        with patch.object(
            api, "fetch_from_api", AsyncMock(return_value=error_response)
        ):
            result = await api.get_news()
        assert "error" in result


# ===========================================================================
# Section B — Integration / live tests
# ===========================================================================


@pytest.mark.integration
class TestFetchFromApiLive:
    """Integration tests that hit the real Tagesschau API.

    Require internet access. Run with: uv run pytest -m integration
    """

    async def test_homepage_returns_news_list(self, live_api):
        """Live homepage endpoint must return a non-empty news list."""
        result = await live_api.fetch_from_api(ENDPOINTS["homepage"])
        assert "error" not in result, f"Live API error: {result.get('message')}"
        assert "news" in result
        assert isinstance(result["news"], list)
        assert len(result["news"]) > 0

    async def test_news_endpoint_returns_items(self, live_api):
        """Live news endpoint must return a news list."""
        result = await live_api.fetch_from_api(ENDPOINTS["news"])
        assert "error" not in result
        assert "news" in result
        assert isinstance(result["news"], list)

    async def test_news_with_ressort_filter(self, live_api):
        """Ressort filter must be accepted by the live API without error."""
        result = await live_api.fetch_from_api(
            ENDPOINTS["news"], {"ressort": "inland"}
        )
        if result.get("error") == "Timeout":
            pytest.skip("Tagesschau API timed out — transient network issue")
        assert "error" not in result
        assert "news" in result

    async def test_news_with_region_filter(self, live_api):
        """Region filter must be accepted by the live API without error."""
        result = await live_api.fetch_from_api(ENDPOINTS["news"], {"regions": "2"})
        assert "error" not in result
        # Region-filtered results are returned under the "news" key;
        # the "regional" key exists in the response but is always empty.
        assert "news" in result
        assert len(result["news"]) > 0

    async def test_search_endpoint_returns_results(self, live_api):
        """Live search endpoint must return a searchResults list."""
        result = await live_api.fetch_from_api(
            ENDPOINTS["search"],
            {"searchText": "Deutschland", "pageSize": "5"},
        )
        assert "error" not in result
        assert "searchResults" in result
        assert isinstance(result["searchResults"], list)

    async def test_channels_endpoint_returns_channels(self, live_api):
        """Live channels endpoint must return a non-empty channels list."""
        result = await live_api.fetch_from_api(ENDPOINTS["channels"])
        assert "error" not in result
        assert "channels" in result
        assert isinstance(result["channels"], list)
        assert len(result["channels"]) > 0

    async def test_get_news_live(self, live_api):
        """Live get_news must return at most <limit> items without error."""
        result = await live_api.get_news(limit=3)
        assert "error" not in result
        assert "items" in result
        assert len(result["items"]) <= 3

    async def test_invalid_endpoint_returns_error_dict(self, live_api):
        """An unknown endpoint must return an error dict, not raise."""
        result = await live_api.fetch_from_api("/api2u/nonexistent_endpoint_xyz")
        assert "error" in result
