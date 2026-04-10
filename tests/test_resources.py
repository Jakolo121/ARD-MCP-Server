"""
Tests for ard_mcp.resources — MCP resource business logic.

Section A: Unit tests with mocked fetch_from_api / get_news.
Section B: Integration tests against the real Tagesschau API.
           Run with: uv run pytest -m integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from ard_mcp.resources import (
    resource_channels,
    resource_homepage,
    resource_news_by_ressort,
    resource_regional_news,
    resource_search,
)

# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
FETCH_PATH = "ard_mcp.resources.fetch_from_api"
GET_NEWS_PATH = "ard_mcp.resources.get_news"


# ===========================================================================
# Section A — Unit / mock tests
# ===========================================================================


class TestResourceHomepageMock:
    """Unit tests for resource_homepage()."""

    async def test_returns_news_formatted(self, homepage_response):
        """Homepage resource must return a formatted news header and items."""
        with patch(FETCH_PATH, AsyncMock(return_value=homepage_response)):
            result = await resource_homepage()
        assert "# Latest News" in result
        assert "Testmeldung" in result

    async def test_api_error_returned(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await resource_homepage()
        assert "Error" in result

    async def test_empty_news_list(self):
        """An empty news list must produce a 'no items' message."""
        with patch(FETCH_PATH, AsyncMock(return_value={"news": []})):
            result = await resource_homepage()
        assert "No news items found" in result


class TestResourceNewsByRessortMock:
    """Unit tests for resource_news_by_ressort()."""

    async def test_invalid_ressort(self):
        """An unknown ressort must be rejected with an 'Invalid ressort' message."""
        result = await resource_news_by_ressort("invalid")
        assert "Invalid ressort" in result

    async def test_valid_ressort(self, news_item):
        """A valid ressort must return formatted news items."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await resource_news_by_ressort("inland")
        assert "Testmeldung" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value=error_response)):
            result = await resource_news_by_ressort("ausland")
        assert "Error" in result

    @pytest.mark.parametrize(
        "ressort",
        ["inland", "ausland", "wirtschaft", "sport",
            "video", "investigativ", "wissen"],
    )
    async def test_all_ressorts_accepted(self, ressort, news_item):
        """Every ressort in the allowed list must be accepted without error."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await resource_news_by_ressort(ressort)
        assert "Invalid" not in result


class TestResourceRegionalNewsMock:
    """Unit tests for resource_regional_news()."""

    async def test_non_numeric_region_id(self):
        """A non-numeric region_id must produce an 'Invalid region ID' error."""
        result = await resource_regional_news("abc")
        assert "Invalid region ID" in result

    async def test_out_of_range_region_id(self):
        """A region_id outside 1–16 must produce an 'Invalid region ID' error."""
        result = await resource_regional_news("99")
        assert "Invalid region ID" in result

    async def test_valid_region_id(self, news_item):
        """A valid string region_id must return formatted regional news."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await resource_regional_news("3")
        assert "Testmeldung" in result

    async def test_invalid_ressort_filter(self):
        """Combining a valid region with an invalid ressort must return an error."""
        result = await resource_regional_news("2", ressort="invalid")
        assert "Invalid ressort" in result

    async def test_valid_ressort_filter(self, news_item):
        """Combining a valid region and ressort must return filtered news."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await resource_regional_news("2", ressort="sport")
        assert "Testmeldung" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value=error_response)):
            result = await resource_regional_news("5")
        assert "Error" in result

    @pytest.mark.parametrize("region_id", [str(i) for i in range(1, 17)])
    async def test_all_valid_region_ids(self, region_id, news_item):
        """All 16 German state IDs must be accepted without an invalid error."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await resource_regional_news(region_id)
        assert "Invalid" not in result


class TestResourceSearchMock:
    """Unit tests for resource_search()."""

    async def test_returns_search_results(self, search_response):
        """Search resource must return formatted results matching the query."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)):
            result = await resource_search("Ukraine")
        assert "Ukraine Neuigkeiten" in result

    async def test_no_results_message(self):
        """Empty search results must produce a 'No results found' message."""
        empty = {"searchResults": [], "totalItemCount": 0}
        with patch(FETCH_PATH, AsyncMock(return_value=empty)):
            result = await resource_search("nothing")
        assert "No results found" in result

    async def test_api_error(self, error_response):
        """An API error during search must be surfaced as an error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await resource_search("test")
        assert "Error" in result

    async def test_page_size_passed_as_string(self, search_response):
        """The pageSize parameter must be forwarded as a string to the API."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)) as mock_fetch:
            await resource_search("test", page_size=5)
        call_params = mock_fetch.call_args[0][1]
        assert call_params["pageSize"] == "5"

    async def test_result_page_passed(self, search_response):
        """The resultPage parameter must be forwarded as a string to the API."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)) as mock_fetch:
            await resource_search("test", result_page=2)
        call_params = mock_fetch.call_args[0][1]
        assert call_params["resultPage"] == "2"

    async def test_page_size_clamped_at_30(self, search_response):
        """A page_size above 30 must be clamped to 30."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)) as mock_fetch:
            await resource_search("test", page_size=999)
        call_params = mock_fetch.call_args[0][1]
        assert call_params["pageSize"] == "30"


class TestResourceChannelsMock:
    """Unit tests for resource_channels()."""

    async def test_returns_channels(self, channels_response):
        """Channels resource must include channel titles in the output."""
        with patch(FETCH_PATH, AsyncMock(return_value=channels_response)):
            result = await resource_channels()
        assert "tagesschau24" in result

    async def test_empty_channels(self):
        """An empty channels list must produce a 'No channels found' message."""
        with patch(FETCH_PATH, AsyncMock(return_value={"channels": []})):
            result = await resource_channels()
        assert "No channels found" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await resource_channels()
        assert "Error" in result

    async def test_streams_rendered(self, channels_response):
        """Stream URLs and labels (Livestream/On-Demand) must appear in the output."""
        with patch(FETCH_PATH, AsyncMock(return_value=channels_response)):
            result = await resource_channels()
        # live stream URL (tagesschau24)
        assert "tagesschau-live.ard-mcdn.de" in result
        # on-demand stream URL (tagesschau in 100 Sekunden)
        assert "tagesschau-progressive.ard-mcdn.de" in result
        # labels are present
        assert "🔴 Livestream" in result
        assert "📼 On-Demand" in result


# ===========================================================================
# Section B — Integration / live tests
# ===========================================================================


@pytest.mark.integration
class TestResourcesLive:
    """Integration tests using the real Tagesschau API.

    Run with: uv run pytest -m integration
    """

    async def test_homepage_resource_live(self):
        """Live homepage resource must return a news header without errors."""
        result = await resource_homepage()
        assert "# Latest News" in result
        assert "Error" not in result

    async def test_news_by_ressort_resource_live(self):
        """Live inland ressort resource must not return an error."""
        result = await resource_news_by_ressort("inland")
        assert "Error" not in result
        assert "Invalid" not in result

    async def test_regional_news_resource_live(self):
        """Live Bavaria regional news resource must not return an error."""
        result = await resource_regional_news("2")
        assert "Error" not in result
        assert "Invalid" not in result

    async def test_search_resource_live(self):
        """Live search resource must not return an error."""
        result = await resource_search("Bundesregierung", page_size=3)
        assert "Error" not in result

    async def test_channels_resource_live(self):
        """Live channels resource must return tagesschau channel entries."""
        result = await resource_channels()
        assert "Error" not in result
        assert "tagesschau" in result.lower()

    async def test_invalid_ressort_resource_live(self):
        """Even live, an invalid ressort should be caught before any network call."""
        result = await resource_news_by_ressort("not_a_real_ressort")
        assert "Invalid ressort" in result

    async def test_invalid_region_resource_live(self):
        """Even live, an invalid region should be caught before any network call."""
        result = await resource_regional_news("999")
        assert "Invalid region ID" in result
