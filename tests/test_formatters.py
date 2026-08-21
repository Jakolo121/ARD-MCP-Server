"""
Unit tests for german_newsfeed_mcp.formatters.

Pure functions — no I/O, no mocking required.
"""

from german_newsfeed_mcp.formatters import (
    _strip_html,
    format_channels,
    format_news_item,
    format_news_list,
)
from tests.conftest import SAMPLE_ARTICLE_DETAILS, SAMPLE_ARTICLE_URL


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------


class TestStripHtml:
    """Tests for _strip_html()."""

    def test_tags_are_removed(self):
        """Markup must disappear while the text content survives."""
        result = _strip_html("<strong>Wichtig</strong> und <em>dringend</em>")
        assert result == "Wichtig und dringend"

    def test_anchor_text_is_kept_without_markup(self):
        """Link text must remain, the href markup must not."""
        result = _strip_html('<a href="https://example.com">Mehr dazu</a>')
        assert result == "Mehr dazu"
        assert "href" not in result

    def test_entities_are_unescaped(self):
        """Named and numeric HTML entities must be decoded."""
        result = _strip_html("B&uuml;rger &amp; St&auml;dte &#8222;Zitat&#8220;")
        assert result == "Bürger & Städte „Zitat“"

    def test_nbsp_becomes_normal_space(self):
        """A non-breaking space must become an ordinary space."""
        result = _strip_html("Wort&nbsp;Wort")
        assert result == "Wort Wort"

    def test_paragraph_end_separates_words(self):
        """Adjacent paragraphs must not be glued together."""
        result = _strip_html("<p>Ende</p><p>Anfang</p>")
        assert "EndeAnfang" not in result
        assert result == "Ende Anfang"

    def test_br_separates_words(self):
        """A line break must not glue the surrounding words."""
        result = _strip_html("Zeile eins<br>Zeile zwei")
        assert "einsZeile" not in result
        assert result == "Zeile eins Zeile zwei"

    def test_list_items_are_separated(self):
        """List items and the closing list tag must produce separation."""
        result = _strip_html("<ul><li>Eins</li><li>Zwei</li></ul>Danach")
        assert "EinsZwei" not in result
        assert result == "Eins Zwei Danach"

    def test_heading_end_separates_words(self):
        """A closing heading tag must not glue heading and body text."""
        result = _strip_html("<h2>Titel</h2>Fliesstext")
        assert result == "Titel Fliesstext"

    def test_whitespace_is_collapsed(self):
        """Runs of whitespace must collapse and be trimmed."""
        result = _strip_html("  viel\n\n   Abstand \t hier  ")
        assert result == "viel Abstand hier"

    def test_empty_input_returns_empty_string(self):
        """Empty input must return an empty string."""
        assert _strip_html("") == ""

    def test_malformed_markup_does_not_raise(self):
        """Unclosed or broken tags must not raise."""
        result = _strip_html("<p>Offen <strong>fett<br>Rest <unbekannt")
        assert "Offen" in result
        assert "fett" in result

    def test_plain_text_is_unchanged(self):
        """Text without markup must pass through unchanged."""
        assert _strip_html("Nur Text.") == "Nur Text."


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

    # --- HTML content vs. firstSentence teaser ---

    def test_homepage_item_content_html_is_stripped(self):
        """Homepage items with HTML content must render as plain text."""
        item = {
            "title": "Homepage-Meldung",
            "content": [
                {"value": "<strong>Erster Absatz.</strong>", "type": "text"},
                {"value": "<p>Zweiter <em>Absatz</em>.</p>", "type": "text"},
            ],
        }
        result = format_news_item(item)
        assert "Erster Absatz." in result
        assert "Zweiter Absatz." in result
        assert "<" not in result

    def test_content_parts_stripped_to_empty_are_skipped(self):
        """content parts that contain only markup must not add blank text."""
        item = {
            "title": "Leere Teile",
            "content": [
                {"value": "<br>"},
                {"value": "<strong>Echter Text</strong>"},
            ],
        }
        result = format_news_item(item)
        assert "Echter Text" in result
        assert "<" not in result

    def test_news_item_without_content_uses_first_sentence(self):
        """Items from /api2u/news must render firstSentence as the body."""
        item = {
            "title": "Meldung ohne Content",
            "topline": "Inland",
            "firstSentence": "Das ist der Teasersatz der Meldung.",
        }
        result = format_news_item(item)
        assert "Das ist der Teasersatz der Meldung." in result

    def test_empty_content_list_falls_back_to_first_sentence(self):
        """An empty content list must not suppress the firstSentence teaser."""
        item = {
            "title": "Leerer Content",
            "content": [],
            "firstSentence": "Teaser trotz leerer Liste.",
        }
        result = format_news_item(item)
        assert "Teaser trotz leerer Liste." in result

    def test_content_wins_over_first_sentence(self):
        """When content exists, firstSentence must not be printed twice."""
        first_sentence = "Das ist der erste Satz."
        item = {
            "title": "Beides vorhanden",
            "content": [{"value": f"<p>{first_sentence}</p> Und mehr Text."}],
            "firstSentence": first_sentence,
        }
        result = format_news_item(item)
        assert result.count(first_sentence) == 1
        assert "Und mehr Text." in result

    def test_neither_content_nor_first_sentence(self):
        """Items with no body at all must still render title, topline and date."""
        item = {
            "title": "Nur Metadaten",
            "topline": "Ausland",
            "date": "2026-04-09T10:00:00.000+02:00",
        }
        result = format_news_item(item)
        assert "Nur Metadaten" in result
        assert "**Ausland**" in result
        assert "2026-04-09" in result

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

    # --- article link: the handle a consumer passes to get_article() ---

    def test_details_renders_volltext_link(self, news_item):
        """The details URL must be rendered as the get_article handle."""
        result = format_news_item(news_item)
        assert f"🔗 Volltext: {SAMPLE_ARTICLE_DETAILS}" in result

    def test_item_without_details_renders_no_link(self):
        """Items without a details field must not render a link line."""
        result = format_news_item({"title": "Ohne Link"})
        assert "🔗" not in result

    def test_link_sits_between_date_and_body(self, news_item):
        """The link must appear after the date and before the body text."""
        result = format_news_item(news_item)
        date_pos = result.index("2026-04-09")
        link_pos = result.index("🔗 Volltext:")
        body_pos = result.index("Das ist der erste Satz")
        assert date_pos < link_pos < body_pos

    def test_foreign_share_url_renders_quelle(self):
        """A shareURL on another ARD host must be named as the source."""
        share_url = "https://www.swr.de/swraktuell/baden-wuerttemberg/x-100.html"
        item = {
            "title": "Regionalmeldung",
            "details": SAMPLE_ARTICLE_DETAILS,
            "shareURL": share_url,
        }
        result = format_news_item(item)
        assert f"📰 Quelle: {share_url}" in result

    def test_same_host_share_url_not_rendered(self, news_item):
        """A shareURL on the same host as details adds no source line."""
        result = format_news_item(news_item)
        assert "📰" not in result

    def test_share_url_without_details_renders_only_quelle(self):
        """Without details there is no handle, but the source is still named."""
        item = {"title": "Nur shareURL", "shareURL": SAMPLE_ARTICLE_URL}
        result = format_news_item(item)
        assert "🔗" not in result
        assert f"📰 Quelle: {SAMPLE_ARTICLE_URL}" in result


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

    def test_article_link_appears_in_list(self, news_item):
        """The get_article handle must propagate through format_news_list."""
        result = format_news_list([news_item])
        assert f"🔗 Volltext: {SAMPLE_ARTICLE_DETAILS}" in result


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
