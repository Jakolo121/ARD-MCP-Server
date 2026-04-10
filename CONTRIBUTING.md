# Contributing to ARD MCP Server

Thank you for your interest in contributing! This document covers everything you need to get started.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Running Tests](#running-tests)
3. [Code Quality](#code-quality)
4. [Project Structure](#project-structure)
5. [PR Workflow](#pr-workflow)
6. [Coding Standards](#coding-standards)

---

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) as its package manager.

```bash
# 1. Clone the repo
git clone https://github.com/Jakolo121/ard_mcp_server.git
cd ard_mcp_server

# 2. Install all dependencies (including dev extras)
uv sync --extra dev

# 3. Verify everything works
make test
```

---

## Running Tests

```bash
# Fast unit tests only (no internet required, ~0.3 s)
make test

# All tests including live API calls
make test-all

# Or directly with uv
uv run pytest tests/ -m "not integration"     # unit only
uv run pytest tests/ -m integration           # live API only
uv run pytest tests/                           # everything
```

### Test markers

| Marker        | Description                                    |
| ------------- | ---------------------------------------------- |
| `integration` | Requires live internet access to tagesschau.de |
| _(none)_      | Fast mock-based unit test                      |

---

## Code Quality

```bash
# Run pylint (must stay at 10.00/10)
make lint

# Combined lint + test
make check
```

The project enforces **pylint 10.00/10**. Pull requests that lower the score will not be merged.

---

## Project Structure

```
src/ard_mcp/
├── __init__.py      # Package metadata (__version__, __author__)
├── config.py        # Environment-variable-driven configuration
├── client.py        # httpx async HTTP client for the Tagesschau API
├── validators.py    # Domain constants (VALID_RESSORTS, VALID_REGION_IDS) + validate_ressort()
├── formatters.py    # Pure Markdown formatters (format_news_item, format_news_list, format_channels)
├── tools.py         # MCP tool implementations (business logic, no decorators)
├── resources.py     # MCP resource implementations (business logic, no decorators)
└── server.py        # FastMCP wiring — applies @mcp.tool() / @mcp.resource() decorators

tests/
├── conftest.py          # Shared fixtures
├── test_client.py       # Tests for client.py
├── test_formatters.py   # Tests for formatters.py
├── test_tools.py        # Tests for tools.py
├── test_resources.py    # Tests for resources.py
```

**Key design decisions:**

- **SRP**: Each module has exactly one reason to change.
- **DIP**: Tools and resources depend on abstractions (`fetch_from_api`, `get_news`), not on httpx directly.
- **Testability**: Business logic in `tools.py` / `resources.py` has zero FastMCP dependency — decorators are applied in `server.py` only.

---

## PR Workflow

1. **Fork** the repository and create a feature branch: `git checkout -b feat/my-feature`
2. Write your code following the [Coding Standards](#coding-standards) below.
3. Add or update tests — coverage for new logic is required.
4. Run `make check` and ensure pylint stays at 10.00/10 and all tests pass.
5. Update `CHANGELOG.md` under `[Unreleased]`.
6. Open a Pull Request with a clear description of what and why.

---

## Coding Standards

- **Python ≥ 3.12** — use modern features (f-strings, `match`, `|` union types where appropriate).
- **uv** for all package management — never use `pip install` directly.
- **Async** — all I/O functions are `async def`; use `httpx.AsyncClient`.
- **Logging** — use lazy `%`-style in `logger.*()` calls; use f-strings everywhere else.
- **Type hints** — all public function signatures must be fully annotated.
- **Docstrings** — Google style for all public functions and modules.
- **SOLID** — single responsibility, open/closed, dependency inversion enforced via pylint.
- **No secrets in code** — all configuration via environment variables.
