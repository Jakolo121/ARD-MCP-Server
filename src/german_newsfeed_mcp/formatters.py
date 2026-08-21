"""
Formatting helpers for Tagesschau news items and channels.

Single Responsibility: convert raw API dicts into human-readable Markdown.
Pure functions — no I/O, no side effects, easy to unit-test.
"""

from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List
from urllib.parse import urlparse

# Tags whose end marks a visual break; text around them must not be glued.
_BREAK_TAGS = frozenset({"br", "p", "h1", "h2", "h3", "h4", "li", "ul", "ol", "div"})


class _TextExtractor(HTMLParser):
    """Collect the plain-text content of an HTML fragment.

    Tags are dropped, their text is kept, and block-level tags emit a
    whitespace separator so words from adjacent blocks stay apart.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.parts.append(unescape(f"&#{name};"))


def _strip_html(raw: str) -> str:
    """Convert an HTML fragment to collapsed plain text.

    Removes all tags, unescapes HTML entities and normalises every run of
    whitespace (including non-breaking spaces) to a single space.

    Args:
        raw: HTML fragment, possibly malformed or empty.

    Returns:
        Plain text without markup, or an empty string for empty input.
    """
    if not raw:
        return ""

    parser = _TextExtractor()
    parser.feed(raw)
    parser.close()
    return " ".join("".join(parser.parts).split())


def _format_streams(streams: Dict[str, Any]) -> List[str]:
    """Render a ``streams`` dict as labelled Markdown lines.

    Distinguishes live HLS streams (URL contains ``tagesschau-live``) from
    on-demand recordings so callers don't have to repeat that logic.

    Args:
        streams: Raw ``streams`` dict from a Tagesschau API item.

    Returns:
        List of Markdown lines (may be empty when ``streams`` is empty).
    """
    if not streams:
        return []

    lines: List[str] = ["📺 **Video-Streams:**"]
    for stream_type, url in streams.items():
        if not isinstance(url, str):
            continue
        # tagesschau-live.ard-mcdn.de → live HLS; everything else → on-demand
        if "tagesschau-live" in url:
            label = f"🔴 Livestream ({stream_type})"
        else:
            label = f"📼 On-Demand ({stream_type})"
        lines.append(f"  - {label}: {url}")
    return lines


def format_news_item(item: Dict[str, Any]) -> str:
    """Format a single news item as Markdown.

    Includes video stream URLs when the item carries a ``streams`` field
    (e.g. ressort=video items) so users don't have to call get_channels()
    just to obtain playback links.

    HTML in ``content`` is stripped to plain text. Items without usable
    ``content`` (the /api2u/news endpoint omits it) fall back to
    ``firstSentence`` so they render more than just a headline.

    Args:
        item: Raw news dict from the Tagesschau API.

    Returns:
        Markdown-formatted string.
    """
    title = item.get("title", "No title")
    topline = item.get("topline", "")
    date = item.get("date", "")

    # content is a list of dicts with a "value" key holding HTML
    content_list = item.get("content", [])
    content = ""
    if isinstance(content_list, list):
        content = " ".join(
            stripped
            for stripped in (
                _strip_html(part.get("value", ""))
                for part in content_list
                if isinstance(part, dict)
            )
            if stripped
        )

    # /api2u/news items carry no content — fall back to the teaser sentence.
    if not content:
        content = _strip_html(item.get("firstSentence", ""))

    parts: List[str] = [f"# {title}"]
    if topline:
        parts.append(f"**{topline}**")
    if date:
        parts.append(f"*{date}*")

    # Handle for get_article(). `details` is the only field that always points
    # at tagesschau.de — shareURL/detailsweb point at the originating ARD state
    # broadcaster (swr.de, mdr.de …) for regional items.
    details = item.get("details", "")
    if details:
        parts.append(f"🔗 Volltext: {details}")

    # Regional items originate at an ARD state broadcaster — name the source.
    share_url = item.get("shareURL", "")
    if share_url and urlparse(share_url).netloc != urlparse(details).netloc:
        parts.append(f"📰 Quelle: {share_url}")

    if content:
        parts.append("")
        parts.append(content)

    # Embed video stream links when the API provides them
    streams = item.get("streams", {})
    if isinstance(streams, dict) and streams:
        parts.append("")
        parts.extend(_format_streams(streams))

    return "\n".join(parts)


def format_news_list(news_items: List[Dict[str, Any]], limit: int = 10) -> str:
    """Format a list of news items as Markdown.

    Args:
        news_items: List of raw news dicts.
        limit:      Maximum number of items to render.

    Returns:
        Markdown-formatted string, or a "no items" message.
    """
    if not news_items:
        return "No news items found."

    items = news_items[:limit]
    sections = ["# Latest News\n"]
    for item in items:
        sections.append(format_news_item(item))
        sections.append("\n---\n")

    return "\n".join(sections)


def format_channels(channels: List[Dict[str, Any]]) -> str:
    """Format a list of channel dicts as Markdown.

    Extracted shared helper used by both tools and resources to avoid
    code duplication (eliminates R0801).

    Clearly distinguishes 🔴 live HLS streams from 📼 on-demand recordings
    so users understand which URLs represent a true live broadcast.
    Only ``tagesschau24`` currently provides a live HLS stream; all other
    channel entries are on-demand recordings of past broadcasts.

    Args:
        channels: List of raw channel dicts from the Tagesschau API.

    Returns:
        Markdown-formatted string listing channels and their stream URLs,
        or a "no channels found" message when the list is empty.
    """
    if not channels:
        return "No channels found."

    lines = [
        "# Tagesschau Channels and Streams",
        "",
        "> 🔴 **Livestream** = live HLS broadcast (tagesschau24 only)  ",
        "> 📼 **On-Demand** = recording of a past broadcast",
        "",
    ]

    for channel in channels:
        title = channel.get("title", "No title")
        date = channel.get("date", "")

        lines.append(f"## {title}")
        if date:
            lines.append(f"*{date}*")

        streams = channel.get("streams", {})
        if isinstance(streams, dict) and streams:
            lines.extend(_format_streams(streams))
        else:
            lines.append("*No streams available.*")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
