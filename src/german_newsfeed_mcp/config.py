"""
Configuration module for the ARD MCP Server.

All settings are driven by environment variables with sensible defaults.
No external dependency required — uses only the standard library.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
#: Which MCP transport to use.
#: - "stdio"            → local Claude Desktop / CLI usage
#: - "sse"             → Server-Sent Events (legacy, still supported)
#: - "streamable_http" → HTTP streaming (remote / Docker, newer clients)
TRANSPORT: str = os.getenv("TRANSPORT", "stdio")

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "4200"))

# ---------------------------------------------------------------------------
# Upstream Tagesschau API
# ---------------------------------------------------------------------------
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://www.tagesschau.de")
API_TIMEOUT: float = float(os.getenv("API_TIMEOUT", "10.0"))

# ---------------------------------------------------------------------------
# Rate limiting & User-Agent
# ---------------------------------------------------------------------------
#: Local token-bucket budget for requests to the upstream API (per hour).
RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "60"))

#: Optional contact info for the User-Agent header; omitted entirely when unset.
USER_AGENT_CONTACT: Optional[str] = os.getenv("USER_AGENT_CONTACT") or None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
_VALID_TRANSPORTS = {"stdio", "sse", "streamable_http"}
if TRANSPORT not in _VALID_TRANSPORTS:
    raise ValueError(
        f"TRANSPORT env var must be one of {sorted(_VALID_TRANSPORTS)}, got {TRANSPORT!r}"
    )

if RATE_LIMIT_PER_HOUR < 1:
    raise ValueError(
        f"RATE_LIMIT_PER_HOUR env var must be >= 1, got {RATE_LIMIT_PER_HOUR}"
    )

logger.debug(
    "Config loaded: transport=%s host=%s port=%d timeout=%.1fs log_level=%s",
    TRANSPORT,
    HOST,
    PORT,
    API_TIMEOUT,
    LOG_LEVEL,
)
