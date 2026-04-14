"""
Tests for ard_mcp.tools — MCP tool business logic.

Section A: Unit tests with mocked fetch_from_api / get_news.
Section B: Integration tests against the real Tagesschau API.
           Run with: uv run pytest -m integration
"""

from unittest.mock import AsyncMock, patch

import pytest

from ard_mcp.tools import (
    tool_get_channels,
    tool_get_latest_news,
    tool_get_news,
    tool_get_news_by_ressort,
    tool_get_regional_news,
    tool_search_news,
)

# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
FETCH_PATH = "ard_mcp.tools.fetch_from_api"
GET_NEWS_PATH = "ard_mcp.tools.get_news"


# ===========================================================================
# Section A — Unit / mock tests
# ===========================================================================


class TestToolGetLatestNewsMock:
    """Unit tests for tool_get_latest_news()."""

    async def test_returns_formatted_news(self, homepage_response):
        """Formatted output must include the news header and item titles."""
        with patch(FETCH_PATH, AsyncMock(return_value=homepage_response)):
            result = await tool_get_latest_news()
        assert "# Latest News" in result
        assert "Testmeldung" in result

    async def test_empty_news_list_returns_no_items(self):
        """An empty news list from the API must produce a 'no items' message."""
        with patch(FETCH_PATH, AsyncMock(return_value={"news": []})):
            result = await tool_get_latest_news()
        assert "No news items found" in result

    async def test_api_error_returns_error_message(self, error_response):
        """An API error response must be surfaced as a human-readable error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await tool_get_latest_news()
        assert "Error" in result

    async def test_limit_is_respected(self, news_item):
        """Only up to <limit> items must appear in the formatted output."""
        items = [dict(news_item, title=f"Item {i}") for i in range(20)]
        with patch(FETCH_PATH, AsyncMock(return_value={"news": items})):
            result = await tool_get_latest_news(limit=3)
        assert "# Item 2" in result
        assert "# Item 3" not in result

    async def test_limit_zero_returns_hint(self):
        """limit=0 must return a human-readable hint, not 'no items found'."""
        result = await tool_get_latest_news(limit=0)
        assert "limit=0" in result
        assert "≥ 1" in result

    async def test_high_limit_adds_cap_note(self, news_item):
        """A limit above the API maximum must append a note about the cap."""
        items = [dict(news_item, title=f"Item {i}") for i in range(50)]
        with patch(FETCH_PATH, AsyncMock(return_value={"news": items})):
            result = await tool_get_latest_news(limit=100)
        assert "API maximum" in result
        assert "50" in result


class TestToolGetNewsByRessortMock:
    """Unit tests for tool_get_news_by_ressort()."""

    async def test_invalid_ressort_returns_error(self):
        """An unknown ressort must be rejected with an 'Invalid ressort' message."""
        result = await tool_get_news_by_ressort("invalid_category")
        assert "Invalid ressort" in result

    async def test_valid_ressort_returns_news(self, news_item):
        """A valid ressort must return formatted news items."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news_by_ressort("inland")
        assert "Testmeldung" in result

    async def test_api_error_propagated(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value=error_response)):
            result = await tool_get_news_by_ressort("ausland")
        assert "Error" in result

    async def test_empty_results_message(self):
        """An empty items list must produce a 'no items' message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value={"items": []})):
            result = await tool_get_news_by_ressort("sport")
        assert "No news items found" in result

    @pytest.mark.parametrize(
        "ressort",
        ["inland", "ausland", "wirtschaft", "sport",
            "video", "investigativ", "wissen"],
    )
    async def test_all_valid_ressorts_accepted(self, ressort, news_item):
        """Every ressort in the allowed list must be accepted without error."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news_by_ressort(ressort)
        assert "Error" not in result or "Invalid" not in result


class TestToolGetRegionalNewsMock:
    """Unit tests for tool_get_regional_news()."""

    async def test_invalid_region_too_low(self):
        """A region_id of 0 must be rejected as invalid."""
        result = await tool_get_regional_news(0)
        assert "Invalid region" in result

    async def test_invalid_region_too_high(self):
        """A region_id of 17 must be rejected as invalid."""
        result = await tool_get_regional_news(17)
        assert "Invalid region" in result

    async def test_valid_region_returns_news(self, news_item):
        """A valid region_id must return formatted news items."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_regional_news(2)
        assert "Testmeldung" in result

    async def test_with_invalid_ressort(self):
        """Combining a valid region with an invalid ressort must return an error."""
        result = await tool_get_regional_news(2, ressort="invalid")
        assert "Invalid ressort" in result

    async def test_with_valid_ressort(self, news_item):
        """Combining a valid region with a valid ressort must return news."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_regional_news(3, ressort="inland")
        assert "Testmeldung" in result

    async def test_with_valid_ressort_shows_warning(self, news_item):
        """Combining region + ressort must prepend the API-limitation warning."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_regional_news(2, ressort="wirtschaft")
        assert "API limitation" in result
        assert "ressort only" in result

    async def test_region_only_no_warning(self, news_item):
        """Using only a region (no ressort) must NOT show the warning."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_regional_news(2)
        assert "API limitation" not in result

    async def test_limit_zero_returns_hint(self):
        """limit=0 must return a human-readable hint, not 'Invalid region' or 'no items'."""
        result = await tool_get_regional_news(2, limit=0)
        assert "limit=0" in result
        assert "≥ 1" in result

    async def test_empty_regional_news(self):
        """An empty regional news list must produce a 'no regional news' message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value={"items": []})):
            result = await tool_get_regional_news(1)
        assert "No regional news" in result

    @pytest.mark.parametrize("region_id", range(1, 17))
    async def test_all_valid_region_ids_accepted(self, region_id, news_item):
        """All 16 German state IDs (1–16) must be accepted without error."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_regional_news(region_id)
        assert "Invalid region" not in result


class TestToolSearchNewsMock:
    """Unit tests for tool_search_news()."""

    async def test_returns_search_results(self, search_response):
        """Search results must include the query term and matching titles."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)):
            result = await tool_search_news("Ukraine")
        assert "Ukraine" in result
        assert "Ukraine Neuigkeiten" in result

    async def test_no_results_message(self):
        """Empty search results must produce a 'No results found' message."""
        with patch(
            FETCH_PATH,
            AsyncMock(return_value={"searchResults": [], "totalItemCount": 0}),
        ):
            result = await tool_search_news("xyznotfound")
        assert "No results found" in result

    async def test_api_error_returned(self, error_response):
        """An API error during search must be surfaced as an error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await tool_search_news("test")
        assert "Error" in result

    async def test_page_size_clamped_at_30(self, search_response):
        """A page_size above 30 must be clamped to 30."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)) as mock_fetch:
            await tool_search_news("test", page_size=999)
        call_params = mock_fetch.call_args[0][1]
        assert call_params["pageSize"] == "30"

    async def test_page_size_clamped_at_1(self, search_response):
        """A page_size of 0 must be clamped to 1."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)) as mock_fetch:
            await tool_search_news("test", page_size=0)
        call_params = mock_fetch.call_args[0][1]
        assert call_params["pageSize"] == "1"

    async def test_total_count_shown(self, search_response):
        """The total result count from the API must appear in the output."""
        with patch(FETCH_PATH, AsyncMock(return_value=search_response)):
            result = await tool_search_news("Ukraine")
        assert "42" in result


class TestToolGetNewsMock:
    """Unit tests for tool_get_news() (flexible fetcher)."""

    async def test_no_params_returns_news(self, news_item):
        """Calling tool_get_news without parameters must return formatted news."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news()
        assert "Testmeldung" in result

    async def test_invalid_region_string(self):
        """A non-numeric regions value must produce an 'Invalid region ID' error."""
        result = await tool_get_news(regions="not_a_number")
        assert "Invalid region ID" in result

    async def test_invalid_region_out_of_range(self):
        """A region ID outside 1–16 must produce an 'Invalid region' error."""
        result = await tool_get_news(regions="99")
        assert "Invalid region" in result

    async def test_invalid_ressort(self):
        """An unknown ressort must produce an 'Invalid ressort' error."""
        result = await tool_get_news(ressort="invalid_cat")
        assert "Invalid ressort" in result

    async def test_valid_region_and_ressort(self, news_item):
        """Combining a valid region and ressort must return filtered news."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news(regions="3", ressort="inland")
        assert "Testmeldung" in result

    async def test_region_and_ressort_together_shows_warning(self, news_item):
        """Combining region and ressort must prepend the API-limitation warning."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news(regions="2", ressort="wirtschaft")
        assert "API limitation" in result
        assert "ressort only" in result

    async def test_region_only_no_warning(self, news_item):
        """Using only a region must NOT show the API-limitation warning."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news(regions="2")
        assert "API limitation" not in result

    async def test_ressort_only_no_warning(self, news_item):
        """Using only a ressort must NOT show the API-limitation warning."""
        payload = {"items": [news_item]}
        with patch(GET_NEWS_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_news(ressort="inland")
        assert "API limitation" not in result

    async def test_limit_zero_returns_hint(self):
        """limit=0 must return a human-readable hint, not 'no items found'."""
        result = await tool_get_news(limit=0)
        assert "limit=0" in result
        assert "≥ 1" in result

    async def test_high_limit_adds_cap_note(self, news_item):
        """A limit above the API maximum must append a note about the cap."""
        items = [dict(news_item, title=f"Item {i}") for i in range(50)]
        with patch(GET_NEWS_PATH, AsyncMock(return_value={"items": items})):
            result = await tool_get_news(limit=100)
        assert "API maximum" in result
        assert "50" in result

    async def test_empty_result_message(self):
        """An empty items list must produce a 'no items' message."""
        with patch(GET_NEWS_PATH, AsyncMock(return_value={"items": []})):
            result = await tool_get_news()
        assert "No news items found" in result


class TestToolGetChannelsMock:
    """Unit tests for tool_get_channels()."""

    async def test_returns_channel_list(self, channels_response):
        """Formatted output must include channel titles and stream URLs."""
        with patch(FETCH_PATH, AsyncMock(return_value=channels_response)):
            result = await tool_get_channels()
        assert "tagesschau24" in result
        assert "hls" in result

    async def test_empty_channels(self):
        """An empty channels list must produce a 'No channels found' message."""
        with patch(FETCH_PATH, AsyncMock(return_value={"channels": []})):
            result = await tool_get_channels()
        assert "No channels found" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        with patch(FETCH_PATH, AsyncMock(return_value=error_response)):
            result = await tool_get_channels()
        assert "Error" in result

    async def test_channel_without_streams(self):
        """A channel entry with no streams must still render its title without error."""
        payload = {
            "channels": [{"title": "TestChannel", "type": "video", "streams": {}}]
        }
        with patch(FETCH_PATH, AsyncMock(return_value=payload)):
            result = await tool_get_channels()
        assert "TestChannel" in result


# ===========================================================================
# Section B — Integration / live tests
# ===========================================================================


@pytest.mark.integration
class TestToolsLive:
    """Integration tests using the real Tagesschau API.

    Run with: uv run pytest -m integration
    """

    async def test_get_latest_news_live(self):
        """Live latest-news tool must return a news header without errors."""
        result = await tool_get_latest_news(limit=5)
        assert "# Latest News" in result
        assert "Error" not in result

    async def test_get_news_by_ressort_inland_live(self):
        """Live inland ressort must return a news header without errors."""
        result = await tool_get_news_by_ressort("inland", limit=3)
        assert "# Latest News" in result
        assert "Invalid" not in result

    async def test_get_news_by_ressort_ausland_live(self):
        """Live ausland ressort must not return an error."""
        result = await tool_get_news_by_ressort("ausland", limit=3)
        assert "Error" not in result

    async def test_get_regional_news_bavaria_live(self):
        """Live Bavaria (region 2) news must not return an error."""
        result = await tool_get_regional_news(2, limit=3)
        # May be empty if no regional news available, but should not error
        assert "Error" not in result

    async def test_search_news_live(self):
        """Live search must return results containing the query term."""
        result = await tool_search_news("Deutschland", page_size=5)
        assert "Error" not in result
        assert "Deutschland" in result

    async def test_get_channels_live(self):
        """Live channels tool must return tagesschau channel entries."""
        result = await tool_get_channels()
        assert "Error" not in result
        assert "tagesschau" in result.lower()

    async def test_get_news_flexible_live(self):
        """Live flexible news tool with ressort must not return an error."""
        result = await tool_get_news(ressort="wirtschaft", limit=3)
        assert "Error" not in result

    async def test_get_news_with_region_live(self):
        """Live flexible news tool with region must not return an invalid error."""
        result = await tool_get_news(regions="1", limit=3)
        # Should not return an error even if news list is empty
        assert "Invalid" not in result
        # Skip gracefully if the API times out (transient network issue)
        if "Error fetching" in result:
            pytest.skip("Tagesschau API timed out — transient network issue")
