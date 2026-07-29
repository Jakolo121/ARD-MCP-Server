"""
Tests for german_newsfeed_mcp.resources — MCP resource business logic.

Section A: Unit tests with an injected FakeNewsApi (no network I/O).
Section B: Integration tests against the real Tagesschau API.
           Run with: uv run pytest -m integration
"""

import pytest

from german_newsfeed_mcp.resources import (
    resource_channels,
    resource_homepage,
    resource_news_by_ressort,
    resource_regional_news,
    resource_search,
)
from tests.conftest import FakeNewsApi

# ===========================================================================
# Section A — Unit / mock tests
# ===========================================================================


class TestResourceHomepageMock:
    """Unit tests for resource_homepage()."""

    async def test_returns_news_formatted(self, homepage_response):
        """Homepage resource must return a formatted news header and items."""
        api = FakeNewsApi(fetch_response=homepage_response)
        result = await resource_homepage(api)
        assert "# Latest News" in result
        assert "Testmeldung" in result

    async def test_api_error_returned(self, error_response):
        """An API error must be surfaced as an error message."""
        api = FakeNewsApi(fetch_response=error_response)
        result = await resource_homepage(api)
        assert "Error" in result

    async def test_empty_news_list(self):
        """An empty news list must produce a 'no items' message."""
        api = FakeNewsApi(fetch_response={"news": []})
        result = await resource_homepage(api)
        assert "No news items found" in result


class TestResourceNewsByRessortMock:
    """Unit tests for resource_news_by_ressort()."""

    async def test_invalid_ressort(self):
        """An unknown ressort must be rejected with an 'Invalid ressort' message."""
        result = await resource_news_by_ressort(FakeNewsApi(), "invalid")
        assert "Invalid ressort" in result

    async def test_valid_ressort(self, news_item):
        """A valid ressort must return formatted news items."""
        api = FakeNewsApi(news_response={"items": [news_item]})
        result = await resource_news_by_ressort(api, "inland")
        assert "Testmeldung" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        api = FakeNewsApi(news_response=error_response)
        result = await resource_news_by_ressort(api, "ausland")
        assert "Error" in result

    @pytest.mark.parametrize(
        "ressort",
        ["inland", "ausland", "wirtschaft", "sport",
            "video", "investigativ", "wissen"],
    )
    async def test_all_ressorts_accepted(self, ressort, news_item):
        """Every ressort in the allowed list must be accepted without error."""
        api = FakeNewsApi(news_response={"items": [news_item]})
        result = await resource_news_by_ressort(api, ressort)
        assert "Invalid" not in result


class TestResourceRegionalNewsMock:
    """Unit tests for resource_regional_news()."""

    async def test_non_numeric_region_id(self):
        """A non-numeric region_id must produce an 'Invalid region ID' error."""
        result = await resource_regional_news(FakeNewsApi(), "abc")
        assert "Invalid region ID" in result

    async def test_out_of_range_region_id(self):
        """A region_id outside 1–16 must produce an 'Invalid region ID' error."""
        result = await resource_regional_news(FakeNewsApi(), "99")
        assert "Invalid region ID" in result

    async def test_valid_region_id(self, news_item):
        """A valid string region_id must return formatted regional news."""
        api = FakeNewsApi(news_response={"items": [news_item]})
        result = await resource_regional_news(api, "3")
        assert "Testmeldung" in result

    async def test_invalid_ressort_filter(self):
        """Combining a valid region with an invalid ressort must return an error."""
        result = await resource_regional_news(FakeNewsApi(), "2", ressort="invalid")
        assert "Invalid ressort" in result

    async def test_valid_ressort_filter(self, news_item):
        """Combining a valid region and ressort must return filtered news."""
        api = FakeNewsApi(news_response={"items": [news_item]})
        result = await resource_regional_news(api, "2", ressort="sport")
        assert "Testmeldung" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        api = FakeNewsApi(news_response=error_response)
        result = await resource_regional_news(api, "5")
        assert "Error" in result

    @pytest.mark.parametrize("region_id", [str(i) for i in range(1, 17)])
    async def test_all_valid_region_ids(self, region_id, news_item):
        """All 16 German state IDs must be accepted without an invalid error."""
        api = FakeNewsApi(news_response={"items": [news_item]})
        result = await resource_regional_news(api, region_id)
        assert "Invalid" not in result


class TestResourceSearchMock:
    """Unit tests for resource_search()."""

    async def test_returns_search_results(self, search_response):
        """Search resource must return formatted results matching the query."""
        api = FakeNewsApi(fetch_response=search_response)
        result = await resource_search(api, "Ukraine")
        assert "Ukraine Neuigkeiten" in result

    async def test_no_results_message(self):
        """Empty search results must produce a 'No results found' message."""
        api = FakeNewsApi(fetch_response={"searchResults": [], "totalItemCount": 0})
        result = await resource_search(api, "nothing")
        assert "No results found" in result

    async def test_api_error(self, error_response):
        """An API error during search must be surfaced as an error message."""
        api = FakeNewsApi(fetch_response=error_response)
        result = await resource_search(api, "test")
        assert "Error" in result

    async def test_page_size_passed_as_string(self, search_response):
        """The pageSize parameter must be forwarded as a string to the API."""
        api = FakeNewsApi(fetch_response=search_response)
        await resource_search(api, "test", page_size=5)
        call_params = api.fetch_from_api.call_args[0][1]
        assert call_params["pageSize"] == "5"

    async def test_result_page_passed(self, search_response):
        """The resultPage parameter must be forwarded as a string to the API."""
        api = FakeNewsApi(fetch_response=search_response)
        await resource_search(api, "test", result_page=2)
        call_params = api.fetch_from_api.call_args[0][1]
        assert call_params["resultPage"] == "2"

    async def test_page_size_clamped_at_30(self, search_response):
        """A page_size above 30 must be clamped to 30."""
        api = FakeNewsApi(fetch_response=search_response)
        await resource_search(api, "test", page_size=999)
        call_params = api.fetch_from_api.call_args[0][1]
        assert call_params["pageSize"] == "30"


class TestResourceChannelsMock:
    """Unit tests for resource_channels()."""

    async def test_returns_channels(self, channels_response):
        """Channels resource must include channel titles in the output."""
        api = FakeNewsApi(fetch_response=channels_response)
        result = await resource_channels(api)
        assert "tagesschau24" in result

    async def test_empty_channels(self):
        """An empty channels list must produce a 'No channels found' message."""
        api = FakeNewsApi(fetch_response={"channels": []})
        result = await resource_channels(api)
        assert "No channels found" in result

    async def test_api_error(self, error_response):
        """An API error must be surfaced as an error message."""
        api = FakeNewsApi(fetch_response=error_response)
        result = await resource_channels(api)
        assert "Error" in result

    async def test_streams_rendered(self, channels_response):
        """Stream URLs and labels (Livestream/On-Demand) must appear in the output."""
        api = FakeNewsApi(fetch_response=channels_response)
        result = await resource_channels(api)
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

    async def test_homepage_resource_live(self, live_api):
        """Live homepage resource must return a news header without errors."""
        result = await resource_homepage(live_api)
        assert "# Latest News" in result
        assert "Error" not in result

    async def test_news_by_ressort_resource_live(self, live_api):
        """Live inland ressort resource must not return an error."""
        result = await resource_news_by_ressort(live_api, "inland")
        assert "Error" not in result
        assert "Invalid" not in result

    async def test_regional_news_resource_live(self, live_api):
        """Live Bavaria regional news resource must not return an error."""
        result = await resource_regional_news(live_api, "2")
        assert "Error" not in result
        assert "Invalid" not in result

    async def test_search_resource_live(self, live_api):
        """Live search resource must not return an error."""
        result = await resource_search(live_api, "Bundesregierung", page_size=3)
        assert "Error" not in result

    async def test_channels_resource_live(self, live_api):
        """Live channels resource must return tagesschau channel entries."""
        result = await resource_channels(live_api)
        assert "Error" not in result
        assert "tagesschau" in result.lower()

    async def test_invalid_ressort_resource_live(self, live_api):
        """Even live, an invalid ressort should be caught before any network call."""
        result = await resource_news_by_ressort(live_api, "not_a_real_ressort")
        assert "Invalid ressort" in result

    async def test_invalid_region_resource_live(self, live_api):
        """Even live, an invalid region should be caught before any network call."""
        result = await resource_regional_news(live_api, "999")
        assert "Invalid region ID" in result
