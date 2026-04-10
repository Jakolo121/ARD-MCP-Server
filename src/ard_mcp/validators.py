"""
Shared validation helpers and domain constants for the ARD MCP Server.

Single Responsibility: pure validation functions and the domain constant sets
they operate on — no I/O, no side effects, fully unit-testable.

Extracted here to:
  - eliminate code duplication (R0801) between tools.py and resources.py
  - give VALID_RESSORTS / VALID_REGION_IDS a single authoritative home
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
VALID_RESSORTS: frozenset = frozenset(
    ["inland", "ausland", "wirtschaft", "sport", "video", "investigativ", "wissen"]
)
VALID_REGION_IDS: frozenset = frozenset(range(1, 17))


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_ressort(ressort: str) -> Optional[str]:
    """Validate a ressort slug.

    Args:
        ressort: The ressort slug to validate.

    Returns:
        ``None`` when valid; a human-readable error string when invalid.
    """
    if ressort not in VALID_RESSORTS:
        return (
            f"Invalid ressort: {ressort!r}. "
            f"Valid options are: {', '.join(sorted(VALID_RESSORTS))}"
        )
    return None
