# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] — 2026-08-21

### Added

- **`get_article(url)`** — returns the full text of a single article on demand; it takes the link now printed with every news item and costs exactly one upstream request per call
- Every news item now renders a `🔗 Volltext:` link, and regional items additionally a `📰 Quelle:` line naming the originating ARD state broadcaster

### Changed

- Article HTML is stripped to plain text before it is handed to the assistant
- News-endpoint items now render their teaser sentence instead of just a headline

### Fixed

- Tool descriptions now state which field set each tool returns — `get_latest_news` delivers the full article text, while `get_news_by_ressort`, `get_regional_news` deliver metadata only (title, topline, date, teaser sentence), and `search_news` delivers title, date and article type
- Removed the incorrect claim of a 50-item upstream maximum — the news endpoint exposes no page-size parameter and decides the response size itself
- Empty or whitespace-only `search_text` is rejected with a clear message instead of leaking a raw upstream HTTP 400
- A negative `limit` now reports the value that was actually passed instead of always saying `limit=0`

### Security

- `get_article` never fetches an arbitrary URL. The supplied link is validated and reduced to a relative path under `/api2u/`, which is then requested from the configured API base URL, so requests to other hosts are structurally impossible.

---

## [1.0.0] — 2026-04-09

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
- `stdio`, `sse`, and `streamable_http` transport support
- Environment-variable-driven configuration (`config.py`)
- `httpx`-based async HTTP client with structured error handling

[2.1.0]: https://github.com/Jakolo121/german-newsfeed-mcp/compare/v2.0.2...v2.1.0
[1.0.0]: https://github.com/Jakolo121/german-newsfeed-mcp/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/Jakolo121/german-newsfeed-mcp/releases/tag/v0.1.0
