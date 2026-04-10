# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-04-09

### Added

- **Production-ready project structure** using `src/` layout
- **`validators.py`** — single authoritative home for `VALID_RESSORTS`, `VALID_REGION_IDS` and `validate_ressort()` helper, eliminating duplicate validation logic across tools and resources
- **`formatters.py`** extended with `format_channels()` — extracted from the duplicated channel-rendering loops in `tools.py` and `resources.py`
- **Docker support** — multi-stage `Dockerfile` (builder → runtime, non-root user, health-check) and `docker-compose.yml` with resource limits and `restart: unless-stopped`
- **`.env.example`** — fully documented environment variable reference
- **147-test suite** — 124 fast unit tests (mock-based, zero network I/O) + 23 live integration tests gated behind the `integration` marker
- **`Makefile`** — `make test`, `make lint`, `make run`, `make docker-build`, `make docker-run`, `make clean`
- **`CONTRIBUTING.md`** — developer setup, PR workflow, coding standards
- **`pyproject.toml`** enriched with `[project.urls]`, PyPI classifiers, `license`, `keywords` and `[tool.pylint.format]`

### Changed

- All `%`-format strings replaced with f-strings (pylint C0209 — 43 occurrences)
- Pylint score raised from **8.58 → 10.00/10**
- `__init__.py` — added `__author__`, `__license__`, `__all__`

### Fixed

- Pylint C0301 (line too long) in `tools.py`
- Pylint W0611 (unused import) in `resources.py`

---

## [0.1.0] — 2026-04-01

### Added

- Initial release
- MCP tools: `get_latest_news`, `get_news_by_ressort`, `get_regional_news`, `search_news`, `get_news`, `get_channels`
- MCP resources: `tagesschau://homepage`, `tagesschau://news/{ressort}`, `tagesschau://regional/{region_id}`, `tagesschau://search/{query}`, `tagesschau://channels`
- `stdio` and `sse` / `streamable_http` transport support
- Environment-variable-driven configuration (`config.py`)
- `httpx`-based async HTTP client with structured error handling

[0.2.0]: https://github.com/Jakolo121/ard_mcp_server/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Jakolo121/ard_mcp_server/releases/tag/v0.1.0
