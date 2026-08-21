"""
Shared validation helpers and domain constants for the German Newsfeed MCP Server.

Single Responsibility: pure validation functions and the domain constant sets
they operate on — no I/O, no side effects, fully unit-testable.

Extracted here to:
  - eliminate code duplication (R0801) between tools.py and resources.py
  - give VALID_RESSORTS / VALID_REGION_IDS a single authoritative home
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from german_newsfeed_mcp import config

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
VALID_RESSORTS: frozenset = frozenset(
    ["inland", "ausland", "wirtschaft", "sport", "video", "investigativ", "wissen"]
)
VALID_REGION_IDS: frozenset = frozenset(range(1, 17))

#: Prefix under which the upstream API serves article JSON.
_API_PATH_PREFIX = "/api2u"

#: An article path is a chain of slug segments ending in .html or .json.
#: Restricting segments to [A-Za-z0-9_-] structurally excludes "..", "%2f",
#: empty segments and backslashes, so no separate check for any of them is needed.
_ARTICLE_PATH_RE = re.compile(r"^(?:/[A-Za-z0-9_-]+)+\.(?:html|json)$")


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def normalise_ressort(ressort: str) -> str:
    """Strip whitespace and normalise a ressort string to lowercase.

    This makes the API forgiving for user-agents and LLMs that may supply
    ``"Inland"``, ``"INLAND"``, or ``" inland "`` instead of ``"inland"``.
    """
    return ressort.strip().lower()


def validate_ressort(ressort: str) -> Optional[str]:
    """Validate a ressort slug.

    Args:
        ressort: The ressort slug to validate (already normalised).

    Returns:
        ``None`` when valid; a human-readable error string when invalid.
    """
    if ressort not in VALID_RESSORTS:
        return (
            f"Invalid ressort: {ressort!r}. "
            f"Valid options are: {', '.join(sorted(VALID_RESSORTS))}"
        )
    return None


def _allowed_host() -> str:
    """Return the only host an article link may point at.

    Derived from ``config.API_BASE_URL`` at call time so the allow-list can
    never drift from the host the client actually talks to.
    """
    return urlparse(config.API_BASE_URL).netloc.lower()


# One return per rejection reason keeps each error message distinct.
# pylint: disable-next=too-many-return-statements
def article_path_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Reduce an untrusted article URL to a relative API path.

    The result is meant to be handed straight to
    ``NewsApiClient.fetch_from_api``, which prepends ``config.API_BASE_URL``.
    Returning a path rather than a URL is what makes fetching an arbitrary
    host structurally impossible.

    Both the human-facing ``.html`` form and the API ``.json`` form are
    accepted; the ``.html`` form is converted by prefixing ``/api2u`` and
    swapping the extension.

    Safety invariant: a returned path always matches
    ``^/api2u/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\\.json$`` and therefore
    contains none of ``//``, ``@``, ``?``, ``#``, ``\\``, ``%``, ``:`` or ``..``.

    Args:
        url: The untrusted article URL, e.g. a ``details`` or ``shareURL``
            value taken from a news item.

    Returns:
        ``(path, None)`` when valid; ``(None, error)`` with a human-readable
        error string when invalid.
    """
    url = url.strip()
    if not url:
        return None, "Invalid article URL: the URL is empty."

    try:
        parsed = urlparse(url)
    except ValueError:
        return None, f"Invalid article URL: {url!r} is not a parsable URL."

    if parsed.scheme != "https":
        return None, (
            f"Invalid article URL: scheme must be 'https', got {parsed.scheme!r}."
        )

    allowed_host = _allowed_host()
    if parsed.netloc.lower() != allowed_host:
        return None, (
            f"Invalid article URL: host must be exactly {allowed_host!r}, "
            f"got {parsed.netloc!r}."
        )

    if parsed.query or parsed.params or parsed.fragment:
        return None, (
            "Invalid article URL: query strings, path parameters and fragments "
            "are not allowed."
        )

    path = parsed.path
    if not _ARTICLE_PATH_RE.match(path):
        return None, (
            f"Invalid article URL: path {path!r} is not an article path "
            "(expected slug segments ending in '.html' or '.json')."
        )

    if path.startswith(f"{_API_PATH_PREFIX}/"):
        if path.endswith(".json"):
            return path, None
        return None, (
            f"Invalid article URL: paths below {_API_PATH_PREFIX!r} must end in "
            "'.json'."
        )

    if path.endswith(".html"):
        return f"{_API_PATH_PREFIX}{path.removesuffix('.html')}.json", None

    return None, (
        f"Invalid article URL: '.json' paths are only valid below "
        f"{_API_PATH_PREFIX!r}."
    )
