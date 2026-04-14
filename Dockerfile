# =============================================================================
# ARD / Tagesschau MCP Server — Docker image
#
# Multi-stage build:
#   builder  – installs dependencies via uv into a virtual-env
#   runtime  – copies only the venv + source, runs as non-root user
#
# Build:
#   docker build -t ard-mcp .
#
# Run (Streamable HTTP / remote):
#   docker run -p 8000:8000 -e TRANSPORT=streamable_http ard-mcp
# =============================================================================

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first (layer-cache friendly)
COPY pyproject.toml uv.lock  README.md ./

# Install production dependencies into /app/.venv (no dev extras)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ ./src/
COPY main.py ./

# Lokales Paket installieren
RUN uv sync --frozen --no-dev

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual-env from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src/ ./src/
COPY main.py ./

# Make venv binaries available
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Runtime defaults (override via -e or docker-compose env_file) ─────────────
ENV TRANSPORT=streamable_http \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT}/health', timeout=3)" || exit 1

CMD ["python", "main.py"]
