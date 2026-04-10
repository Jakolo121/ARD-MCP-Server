"""
Tests for ard_mcp.client — HTTP client layer.

Section A: Unit tests using unittest.mock (no network I/O).
Section B: Integration tests against the real Tagesschau API.
           These are marked with @pytest.mark.integration and require
           an internet connection.  Run them explicitly with:
               uv run pytest -m integration
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ard_mcp.client import ENDPOINTS, fetch_from_api, get_news


# ===========================================================================
# Section A — Unit / mock tests
# ===========================================================================


class TestFetchFromApiMock:
    """Unit tests for fetch_from_api using mocked httpx."""

    async def test_successful_response_returns_json(self):
        """A 200 response must be parsed and returned as a dict."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"news": [], "type": "news"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert "news" in result
        assert result["type"] == "news"

    async def test_http_status_error_returns_error_dict(self):
        """An HTTP error status must be returned as an error dict."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "503", request=MagicMock(), response=mock_response
            )
        )

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert "error" in result
        assert "message" in result

    async def test_timeout_returns_error_dict(self):
        """A timeout must be returned as an error dict with error='Timeout'."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Timeout"

    async def test_request_error_returns_error_dict(self):
        """A network request error must be returned as an error dict."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Request error"

    async def test_json_decode_error_returns_error_dict(self):
        """A malformed JSON body must be returned as an error dict."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError(
            "bad json", "", 0)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Invalid JSON response"

    async def test_unexpected_exception_returns_error_dict(self):
        """Any unexpected exception must be caught and returned as an error dict."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected!"))

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_from_api(ENDPOINTS["news"])

        assert result["error"] == "Unknown error"

    async def test_params_are_forwarded(self):
        """Query parameters passed to fetch_from_api must be forwarded to httpx."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"news": [], "regional": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ard_mcp.client.httpx.AsyncClient", return_value=mock_client):
            await fetch_from_api(ENDPOINTS["news"], {"ressort": "inland"})

        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs["params"] == {"ressort": "inland"}


class TestGetNewsMock:
    """Unit tests for the get_news() convenience wrapper."""

    async def test_returns_news_key_by_default(self):
        """Without filters, get_news must return items from the 'news' key."""
        payload = {"news": [{"title": "Foo"}], "regional": [{"title": "Bar"}]}
        with patch("ard_mcp.client.fetch_from_api", AsyncMock(return_value=payload)):
            result = await get_news()
        assert result["items"] == [{"title": "Foo"}]

    async def test_returns_news_key_when_regions_param_given(self):
        """Region-filtered results must still be taken from the 'news' key."""
        # The Tagesschau API always returns region-filtered results under the
        # "news" key; the "regional" key is always empty for this endpoint.
        payload = {"news": [{"title": "Bayern News"}], "regional": []}
        with patch("ard_mcp.client.fetch_from_api", AsyncMock(return_value=payload)):
            result = await get_news(params={"regions": "2"})
        assert result["items"] == [{"title": "Bayern News"}]

    async def test_limit_is_applied(self):
        """The limit parameter must slice the returned items list."""
        items = [{"title": f"Item {i}"} for i in range(20)]
        payload = {"news": items, "regional": []}
        with patch("ard_mcp.client.fetch_from_api", AsyncMock(return_value=payload)):
            result = await get_news(limit=5)
        assert len(result["items"]) == 5

    async def test_propagates_error_response(self, error_response):
        """An error response from the API must be forwarded unchanged."""
        with patch(
            "ard_mcp.client.fetch_from_api", AsyncMock(
                return_value=error_response)
        ):
            result = await get_news()
        assert "error" in result


# ===========================================================================
# Section B — Integration / live tests
# ===========================================================================


@pytest.mark.integration
class TestFetchFromApiLive:
    """Integration tests that hit the real Tagesschau API.

    Require internet access. Run with: uv run pytest -m integration
    """

    async def test_homepage_returns_news_list(self):
        """Live homepage endpoint must return a non-empty news list."""
        result = await fetch_from_api(ENDPOINTS["homepage"])
        assert "error" not in result, f"Live API error: {result.get('message')}"
        assert "news" in result
        assert isinstance(result["news"], list)
        assert len(result["news"]) > 0

    async def test_news_endpoint_returns_items(self):
        """Live news endpoint must return a news list."""
        result = await fetch_from_api(ENDPOINTS["news"])
        assert "error" not in result
        assert "news" in result
        assert isinstance(result["news"], list)

    async def test_news_with_ressort_filter(self):
        """Ressort filter must be accepted by the live API without error."""
        result = await fetch_from_api(ENDPOINTS["news"], {"ressort": "inland"})
        if result.get("error") == "Timeout":
            pytest.skip("Tagesschau API timed out — transient network issue")
        assert "error" not in result
        assert "news" in result

    async def test_news_with_region_filter(self):
        """Region filter must be accepted by the live API without error."""
        result = await fetch_from_api(ENDPOINTS["news"], {"regions": "2"})
        assert "error" not in result
        # Region-filtered results are returned under the "news" key;
        # the "regional" key exists in the response but is always empty.
        assert "news" in result
        assert len(result["news"]) > 0

    async def test_search_endpoint_returns_results(self):
        """Live search endpoint must return a searchResults list."""
        result = await fetch_from_api(
            ENDPOINTS["search"],
            {"searchText": "Deutschland", "pageSize": "5"},
        )
        assert "error" not in result
        assert "searchResults" in result
        assert isinstance(result["searchResults"], list)

    async def test_channels_endpoint_returns_channels(self):
        """Live channels endpoint must return a non-empty channels list."""
        result = await fetch_from_api(ENDPOINTS["channels"])
        assert "error" not in result
        assert "channels" in result
        assert isinstance(result["channels"], list)
        assert len(result["channels"]) > 0

    async def test_get_news_live(self):
        """Live get_news must return at most <limit> items without error."""
        result = await get_news(limit=3)
        assert "error" not in result
        assert "items" in result
        assert len(result["items"]) <= 3

    async def test_invalid_endpoint_returns_error_dict(self):
        """An unknown endpoint must return an error dict, not raise."""
        result = await fetch_from_api("/api2u/nonexistent_endpoint_xyz")
        assert "error" in result
