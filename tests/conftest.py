"""
Shared pytest fixtures for the German Newsfeed MCP test suite.

Provides:
- Mock API response payloads that mirror the real Tagesschau API schema.
- FakeNewsApi: a test double for client.NewsApiClient (unit tests).
- live_api: a real NewsApiClient for integration tests.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from german_newsfeed_mcp.client import NewsApiClient, build_user_agent
from german_newsfeed_mcp.rate_limiter import TokenBucketRateLimiter


# ---------------------------------------------------------------------------
# URL constants (extracted to keep lines within the 100-character limit)
# ---------------------------------------------------------------------------

_URL_H264M = (
    "https://tagesschau-progressive.ard-mcdn.de"
    "/video/2026/0409/clip.webm.h264.mp4"
)
_URL_ADAPTIVE_VOD = (
    "https://adaptive.tagesschau.de"
    "/i/video/2026/0409/clip.mp4.csmil/master.m3u8"
)
_URL_ADAPTIVE_LIVE = (
    "https://tagesschau-live.ard-mcdn.de"
    "/tagesschau/live/hls/de/master.m3u8"
)


# ---------------------------------------------------------------------------
# Sample API payloads  (structure mirrors the real Tagesschau API)
# ---------------------------------------------------------------------------

SAMPLE_NEWS_ITEM = {
    "sophoraId": "abc123",
    "title": "Testmeldung: Wichtige Neuigkeit",
    "topline": "Breaking",
    "date": "2026-04-09T10:00:00.000+02:00",
    "content": [
        {"value": "Das ist der erste Satz der Nachricht."},
        {"value": "Und hier kommt noch mehr Text."},
    ],
    "details": "https://www.tagesschau.de/detail/abc123",
    "detailsweb": "https://www.tagesschau.de/detail/abc123-web",
    "shareURL": "https://www.tagesschau.de/share/abc123",
    "ressort": "inland",
    "type": "story",
    "breakingNews": False,
}

SAMPLE_VIDEO_NEWS_ITEM = {
    "sophoraId": "video-999",
    "title": "Videobeitrag: Wichtige Sendung",
    "date": "2026-04-09T17:00:00.000+02:00",
    "content": [],
    "type": "video",
    "streams": {
        "h264m": _URL_H264M,
        "adaptivestreaming": _URL_ADAPTIVE_VOD,
    },
}

SAMPLE_NEWS_ITEM_MINIMAL = {
    "title": "Minimalmeldung",
}

SAMPLE_REGIONAL_ITEM = {
    "sophoraId": "reg456",
    "title": "Regionalnachricht Bayern",
    "topline": "Bayern",
    "date": "2026-04-09T09:00:00.000+02:00",
    "content": [{"value": "Neuigkeit aus Bayern."}],
    "type": "story",
    "regionId": "2",
}

SAMPLE_HOMEPAGE_RESPONSE = {
    "news": [SAMPLE_NEWS_ITEM],
    "regional": [SAMPLE_REGIONAL_ITEM],
    "type": "news",
}

SAMPLE_NEWS_RESPONSE = {
    "news": [SAMPLE_NEWS_ITEM, SAMPLE_NEWS_ITEM_MINIMAL],
    "regional": [SAMPLE_REGIONAL_ITEM],
    "type": "news page",
}

SAMPLE_SEARCH_RESPONSE = {
    "searchText": "Ukraine",
    "totalItemCount": 42,
    "searchResults": [
        {
            "sophoraId": "s001",
            "title": "Ukraine Neuigkeiten",
            "date": "2026-04-09T08:00:00.000+02:00",
            "type": "story",
        },
        {
            "sophoraId": "s002",
            "title": "Weitere Ukraine-Berichte",
            "date": "2026-04-09T07:00:00.000+02:00",
            "type": "video",
        },
    ],
    "type": "search",
}

SAMPLE_CHANNELS_RESPONSE = {
    "channels": [
        {
            "title": "Im Livestream: tagesschau24",
            "type": "video",
            "streams": {
                "adaptivestreaming": _URL_ADAPTIVE_LIVE,
            },
        },
        {
            "title": "tagesschau in 100 Sekunden",
            "type": "video",
            "date": "2026-04-09T16:42:36.442+02:00",
            "streams": {
                "h264m": _URL_H264M,
                "adaptivestreaming": _URL_ADAPTIVE_VOD,
            },
        },
        {
            "title": "Sendung ohne Streams",
            "type": "video",
            "streams": {},
        },
    ],
    "type": "channels",
}

ERROR_RESPONSE = {"error": "HTTP error",
                  "message": "Status 500 — Internal Server Error"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def news_item():
    """Return a single sample news item dict."""
    return dict(SAMPLE_NEWS_ITEM)


@pytest.fixture()
def video_news_item():
    """Return a sample video news item with stream URLs."""
    return dict(SAMPLE_VIDEO_NEWS_ITEM)


@pytest.fixture()
def homepage_response():
    """Return a sample homepage API response."""
    return dict(SAMPLE_HOMEPAGE_RESPONSE)


@pytest.fixture()
def news_response():
    """Return a sample news API response."""
    return dict(SAMPLE_NEWS_RESPONSE)


@pytest.fixture()
def search_response():
    """Return a sample search API response."""
    return dict(SAMPLE_SEARCH_RESPONSE)


@pytest.fixture()
def channels_response():
    """Return a sample channels API response."""
    return dict(SAMPLE_CHANNELS_RESPONSE)


@pytest.fixture()
def error_response():
    """Return a sample error dict (as returned by fetch_from_api on failure)."""
    return dict(ERROR_RESPONSE)


# ---------------------------------------------------------------------------
# API client test doubles
# ---------------------------------------------------------------------------


class FakeNewsApi:
    """Test double for client.NewsApiClient.

    fetch_from_api / get_news are AsyncMocks, so tests can both stub
    return values and assert on call arguments.
    """

    def __init__(self, fetch_response=None, news_response=None):
        self.fetch_from_api = AsyncMock(return_value=fetch_response)
        self.get_news = AsyncMock(return_value=news_response)


@pytest.fixture()
async def live_api():
    """Real NewsApiClient for integration tests (internet required)."""
    http_client = httpx.AsyncClient(headers={"User-Agent": build_user_agent()})
    yield NewsApiClient(
        http_client=http_client,
        rate_limiter=TokenBucketRateLimiter(capacity=60),
    )
    await http_client.aclose()
