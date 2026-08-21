"""
Unit tests for german_newsfeed_mcp.validators.

Pure functions — no I/O, no mocking required.

The bulk of this file covers ``article_path_from_url``, the security boundary
of the ``get_article`` tool: it takes an untrusted URL and must either reduce
it to a relative path below ``/api2u`` or reject it outright.
"""

import pytest

from german_newsfeed_mcp import config
from german_newsfeed_mcp.validators import (
    article_path_from_url,
    normalise_ressort,
    validate_ressort,
)
from tests.conftest import (
    SAMPLE_ARTICLE_DETAILS,
    SAMPLE_ARTICLE_PATH,
    SAMPLE_ARTICLE_URL,
)

# ---------------------------------------------------------------------------
# Every URL that must be accepted, reused by the invariant test below.
# ---------------------------------------------------------------------------
ACCEPTED_URLS = [
    SAMPLE_ARTICLE_DETAILS,
    SAMPLE_ARTICLE_URL,
    "https://www.tagesschau.de/ausland/x-100.html",
    "https://WWW.TAGESSCHAU.DE/inland/x-100.html",
    f"  {SAMPLE_ARTICLE_URL}  ",
    "https://www.tagesschau.de/inland/x\n-100.html",
]

REJECTED_URLS = [
    pytest.param("", id="empty"),
    pytest.param("   ", id="whitespace-only"),
    pytest.param("http://www.tagesschau.de/inland/x-100.html", id="http-scheme"),
    pytest.param("//www.tagesschau.de/inland/x-100.html", id="protocol-relative"),
    pytest.param("javascript:alert(1)", id="javascript-scheme"),
    pytest.param("file:///etc/passwd", id="file-scheme"),
    pytest.param("https://evil-tagesschau.de/x-100.html", id="host-prefix-attack"),
    pytest.param("https://www.tagesschau.de.evil.com/x-100.html", id="host-suffix-attack"),
    pytest.param("https://evil.com/inland/x-100.html", id="foreign-host"),
    pytest.param("https://user@www.tagesschau.de/x-100.html", id="userinfo"),
    pytest.param("https://www.tagesschau.de@evil.com/x-100.html", id="userinfo-lookalike"),
    pytest.param("https://www.tagesschau.de:8080/x-100.html", id="explicit-port"),
    pytest.param("https://www.tagesschau.de\\@evil.com/x-100.html", id="backslash-userinfo"),
    pytest.param("https://www.tagesschau.de/inland/x-100.html?utm=1", id="query-string"),
    pytest.param("https://www.tagesschau.de/inland/x-100.html#top", id="fragment"),
    pytest.param("https://www.tagesschau.de/inland/x-100.html;p=1", id="path-params"),
    pytest.param("https://www.tagesschau.de/../etc/passwd.html", id="dot-dot-traversal"),
    pytest.param("https://www.tagesschau.de/inland/..%2f..%2fadmin.html", id="encoded-traversal"),
    pytest.param("https://www.tagesschau.de//inland/x-100.html", id="empty-segment"),
    pytest.param("https://www.tagesschau.de/inland/x-100", id="no-extension"),
    pytest.param("https://www.tagesschau.de/inland/x-100.php", id="wrong-extension"),
    pytest.param("https://www.tagesschau.de/", id="root-path"),
    pytest.param("https://www.tagesschau.de", id="host-only"),
    pytest.param("https://[::1/x.html", id="unparsable-ipv6"),
    pytest.param("hello world", id="not-a-url"),
    pytest.param("https://www.tagesschau.de/inland/x-100.json", id="json-outside-api2u"),
    pytest.param("https://www.tagesschau.de/api2u/inland/x-100.html", id="html-inside-api2u"),
]


# ---------------------------------------------------------------------------
# article_path_from_url — accepted input
# ---------------------------------------------------------------------------


class TestArticlePathAccepts:
    """URLs that must be reduced to a relative API path."""

    def test_api_details_url_passes_through_unchanged(self):
        """An /api2u/....json URL is already a valid path and must be kept verbatim."""
        path, error = article_path_from_url(SAMPLE_ARTICLE_DETAILS)
        assert error is None
        assert path == SAMPLE_ARTICLE_PATH

    def test_html_url_is_converted_to_api_json_path(self):
        """The human-facing .html URL must become the matching /api2u/....json path."""
        path, error = article_path_from_url(SAMPLE_ARTICLE_URL)
        assert error is None
        assert path == SAMPLE_ARTICLE_PATH

    def test_two_segment_path_is_converted(self):
        """Conversion must work for any segment depth, not just the sample."""
        path, error = article_path_from_url("https://www.tagesschau.de/ausland/x-100.html")
        assert error is None
        assert path == "/api2u/ausland/x-100.json"

    def test_uppercase_host_is_accepted(self):
        """Host comparison is case-insensitive, as DNS is."""
        path, error = article_path_from_url("https://WWW.TAGESSCHAU.DE/inland/x-100.html")
        assert error is None
        assert path == "/api2u/inland/x-100.json"

    def test_surrounding_whitespace_is_stripped(self):
        """Leading and trailing whitespace must not make a valid URL invalid."""
        path, error = article_path_from_url(f"  {SAMPLE_ARTICLE_URL}  ")
        assert error is None
        assert path == SAMPLE_ARTICLE_PATH

    def test_embedded_newline_is_removed_by_urlparse(self):
        """urlparse strips ASCII newlines/tabs (bpo-43882) — none may reach the path."""
        path, error = article_path_from_url("https://www.tagesschau.de/inland/x\n-100.html")
        assert error is None
        assert path == "/api2u/inland/x-100.json"
        assert "\n" not in path

    @pytest.mark.parametrize("url", ACCEPTED_URLS)
    def test_accepted_paths_satisfy_the_security_invariant(self, url):
        """Whatever is returned must be a relative /api2u/... .json path."""
        path, error = article_path_from_url(url)
        assert error is None
        assert path.startswith("/api2u/")
        assert path.endswith(".json")


class TestArticlePathHostIsReadAtCallTime:
    """The allow-list must follow config.API_BASE_URL, not freeze at import time."""

    def test_patched_base_url_becomes_the_allowed_host(self, monkeypatch):
        """After patching API_BASE_URL the new host is accepted."""
        monkeypatch.setattr(config, "API_BASE_URL", "https://news.example.org")
        path, error = article_path_from_url("https://news.example.org/inland/x-100.html")
        assert error is None
        assert path == "/api2u/inland/x-100.json"

    def test_patched_base_url_rejects_the_previous_host(self, monkeypatch):
        """After patching API_BASE_URL the old host is no longer accepted."""
        monkeypatch.setattr(config, "API_BASE_URL", "https://news.example.org")
        path, error = article_path_from_url(SAMPLE_ARTICLE_URL)
        assert path is None
        assert error is not None
        assert "Invalid article URL" in error


# ---------------------------------------------------------------------------
# article_path_from_url — rejected input
# ---------------------------------------------------------------------------


class TestArticlePathRejects:
    """URLs that must never be turned into a fetchable path."""

    @pytest.mark.parametrize("url", REJECTED_URLS)
    def test_rejected(self, url):
        """Each hostile or malformed URL must be rejected with an error string."""
        path, error = article_path_from_url(url)
        assert path is None
        assert error is not None
        assert "Invalid article URL" in error


# ---------------------------------------------------------------------------
# Ressort validation
# ---------------------------------------------------------------------------


class TestRessortValidation:
    """Tests for normalise_ressort() and validate_ressort()."""

    def test_normalise_strips_and_lowercases(self):
        """Padding and casing must not matter to callers."""
        assert normalise_ressort("  Inland ") == "inland"

    def test_known_ressort_is_valid(self):
        """A ressort from VALID_RESSORTS must produce no error."""
        assert validate_ressort("wirtschaft") is None

    def test_unknown_ressort_is_reported(self):
        """An unknown ressort must be named in the error alongside the valid options."""
        error = validate_ressort("kultur")
        assert error is not None
        assert "kultur" in error
