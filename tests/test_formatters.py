"""
Unit tests for ard_mcp.formatters.

Pure functions — no I/O, no mocking required.
"""

from ard_mcp.formatters import format_channels, format_news_item, format_news_list


# ---------------------------------------------------------------------------
# format_news_item
# ---------------------------------------------------------------------------


class TestFormatNewsItem:
    """Tests for format_news_item()."""

    def test_full_item_contains_title(self, news_item):
        """Title field must appear in the formatted output."""
        result = format_news_item(news_item)
        assert "Testmeldung: Wichtige Neuigkeit" in result

    def test_full_item_contains_topline(self, news_item):
        """Topline field must appear in the formatted output."""
        result = format_news_item(news_item)
        assert "Breaking" in result

    def test_full_item_contains_date(self, news_item):
        """Date field must appear in the formatted output."""
        result = format_news_item(news_item)
        assert "2026-04-09" in result

    def test_full_item_merges_content(self, news_item):
        """All content paragraphs must be merged into the output."""
        result = format_news_item(news_item)
        assert "Das ist der erste Satz" in result
        assert "Und hier kommt noch mehr Text" in result

    def test_minimal_item_no_crash(self):
        """An item with only a title should still render without error."""
        result = format_news_item({"title": "Nur ein Titel"})
        assert "Nur ein Titel" in result

    def test_empty_item_shows_fallback(self):
        """An empty dict should render the 'No title' fallback."""
        result = format_news_item({})
        assert "No title" in result

    def test_non_dict_content_items_are_skipped(self):
        """content list entries that are not dicts must not raise."""
        item = {
            "title": "Test",
            "content": ["not a dict", None, {"value": "good part"}],
        }
        result = format_news_item(item)
        assert "good part" in result

    def test_missing_topline_not_rendered(self):
        """Items without a topline must not produce bold markdown text."""
        result = format_news_item({"title": "Kein Topline"})
        assert "**" not in result

    def test_title_is_h1(self, news_item):
        """The title must be rendered as a first-level markdown heading."""
        result = format_news_item(news_item)
        assert result.startswith("# ")

    # --- Problem 1: video stream URLs ---

    def test_video_item_contains_stream_section(self, video_news_item):
        """Video items must include a 'Video-Streams' section."""
        result = format_news_item(video_news_item)
        assert "Video-Streams" in result

    def test_video_item_on_demand_stream_url_present(self, video_news_item):
        """On-demand .mp4 URLs must be shown in the output."""
        result = format_news_item(video_news_item)
        assert "clip.webm.h264.mp4" in result

    def test_video_item_adaptive_stream_url_present(self, video_news_item):
        """Adaptive streaming URL must be shown in the output."""
        result = format_news_item(video_news_item)
        assert "master.m3u8" in result

    def test_video_item_on_demand_label(self, video_news_item):
        """Non-live streams must be labelled as On-Demand."""
        result = format_news_item(video_news_item)
        assert "On-Demand" in result

    def test_story_item_without_streams_has_no_stream_section(self, news_item):
        """Regular story items without a streams field must not show the stream section."""
        result = format_news_item(news_item)
        assert "Video-Streams" not in result

    def test_livestream_url_gets_live_label(self):
        """A stream URL containing 'tagesschau-live' must be labelled as Livestream."""
        item = {
            "title": "Live Test",
            "type": "video",
            "streams": {
                "adaptivestreaming": (
                    "https://tagesschau-live.ard-mcdn.de"
                    "/tagesschau/live/hls/de/master.m3u8"
                )
            },
        }
        result = format_news_item(item)
        assert "🔴 Livestream" in result

    def test_empty_streams_dict_skipped(self):
        """An item with an empty streams dict must not crash and not add the stream section."""
        item = {"title": "Kein Stream", "streams": {}}
        result = format_news_item(item)
        assert "Video-Streams" not in result


# ---------------------------------------------------------------------------
# format_news_list
# ---------------------------------------------------------------------------


class TestFormatNewsList:
    """Tests for format_news_list()."""

    def test_empty_list_returns_no_items_message(self):
        """An empty list must return the 'No news items found.' message."""
        assert format_news_list([]) == "No news items found."

    def test_single_item_contains_title(self, news_item):
        """A list with one item must include that item's title."""
        result = format_news_list([news_item])
        assert "Testmeldung" in result

    def test_respects_limit(self, news_item):
        """Only up to <limit> items must be rendered."""
        items = [dict(news_item, title=f"Item {i}") for i in range(20)]
        result = format_news_list(items, limit=5)
        # 5 items means 5 "# Item N" headlines; "Item 5" should NOT appear
        assert "# Item 4" in result
        assert "# Item 5" not in result

    def test_default_limit_is_10(self, news_item):
        """Without an explicit limit, at most 10 items must be rendered."""
        items = [dict(news_item, title=f"Item {i}") for i in range(15)]
        result = format_news_list(items)
        assert "# Item 9" in result
        assert "# Item 10" not in result

    def test_separator_present(self, news_item):
        """A horizontal rule must appear between multiple items."""
        result = format_news_list([news_item, news_item])
        assert "---" in result

    def test_header_present(self, news_item):
        """The output must start with a '# Latest News' header."""
        result = format_news_list([news_item])
        assert "# Latest News" in result

    def test_video_item_streams_appear_in_list(self, video_news_item):
        """Stream links must propagate through format_news_list."""
        result = format_news_list([video_news_item])
        assert "Video-Streams" in result
        assert "clip.webm.h264.mp4" in result


# ---------------------------------------------------------------------------
# format_channels
# ---------------------------------------------------------------------------


class TestFormatChannels:
    """Tests for format_channels() — Problem 3: Livestream vs. On-Demand."""

    def test_empty_channels_returns_message(self):
        """An empty channel list must return the 'No channels found.' message."""
        assert format_channels([]) == "No channels found."

    def test_contains_channel_title(self, channels_response):
        """Channel titles must appear in the formatted output."""
        result = format_channels(channels_response["channels"])
        assert "tagesschau24" in result

    def test_live_url_gets_livestream_label(self, channels_response):
        """The tagesschau24 channel with a -live. URL must be labelled as Livestream."""
        result = format_channels(channels_response["channels"])
        assert "🔴 Livestream" in result

    def test_on_demand_url_gets_on_demand_label(self, channels_response):
        """Progressive/adaptive URLs must be labelled as On-Demand."""
        result = format_channels(channels_response["channels"])
        assert "📼 On-Demand" in result

    def test_legend_present(self, channels_response):
        """The legend explaining 🔴/📼 must appear in the output."""
        result = format_channels(channels_response["channels"])
        assert "🔴" in result
        assert "📼" in result

    def test_channel_without_streams_shows_no_streams_message(self, channels_response):
        """A channel entry with an empty streams dict must show 'No streams available'."""
        result = format_channels(channels_response["channels"])
        assert "No streams available" in result

    def test_live_url_not_labelled_as_on_demand(self, channels_response):
        """The live HLS URL must not be incorrectly tagged as On-Demand."""
        result = format_channels(channels_response["channels"])
        # Find the section for the live channel and confirm On-Demand doesn't appear
        # right after it by checking the live URL line itself
        live_url = "tagesschau-live.ard-mcdn.de"
        assert live_url in result
        # The line containing the live URL must have Livestream label, not On-Demand
        live_line = next(
            line for line in result.splitlines() if live_url in line
        )
        assert "Livestream" in live_line
        assert "On-Demand" not in live_line

    def test_separator_between_channels(self, channels_response):
        """A horizontal rule must appear between channel entries."""
        result = format_channels(channels_response["channels"])
        assert "---" in result
