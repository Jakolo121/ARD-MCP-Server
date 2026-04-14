# 🎙️ ARD / Tagesschau MCP Server

> **Bring live German news directly into your AI chat.**  
> A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that wraps the public Tagesschau API. This README assists you from a local to full Docker deployment.

![pylint](https://img.shields.io/badge/pylint-10.00%2F10-brightgreen)
![tests](https://img.shields.io/badge/tests-124%20passed-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-blue)

Language:

- 🇩🇪 [Deutsch] (README_en.md)
- 🇬🇧 English

---

## Table of Contents

1. [What is this?](#what-is-this)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Quick Start Local deployment (Example: claude Desktop](#quick-start--local-claude-desktop)
5. [Remote / Docker Deployment](#remote--docker-deployment)
6. [Configuration Reference](#configuration-reference)
7. [Available Tools](#available-tools)
8. [Available Resources](#available-resources)
9. [Development Guide](#development-guide)
10. [Running the Tests](#running-the-tests)
11. [Makefile Reference](#makefile-reference)
12. [Troubleshooting](#troubleshooting)

---

## What is this?

This project is an MCP server that brings ARD News into a AI assistants (Claude, Open Claw etc.) can call at runtime. Let the machines acces your Content and you decide how they do!

Once connected, your AI can answer questions like:

- _"Was sind die aktuellen Schlagzeilen?"_
- _"Zeig mir die neuesten Wirtschaftsnachrichten."_
- _"Suche nach Artikeln über Ukraine."_
- _"Welche Regionalnachrichten gibt es aus Bayern?"_

All data comes from the official, public [Tagesschau API](https://www.tagesschau.de/api2u/) — no API key required.

---

## Features

|                         |                                                                         |
| ----------------------- | ----------------------------------------------------------------------- |
| 🗞️ **Live news**        | Fetches breaking news, categorised news, and regional news in real time |
| 🔍 **Full-text search** | Search across all Tagesschau articles                                   |
| 📺 **Live streams**     | List all available Tagesschau channels and HLS stream URLs              |
| 🚀 **Dual transport**   | `stdio` for local Claude Desktop; `streamable_http` for remote / Docker |
| 🐳 **Docker-ready**     | Multi-stage image, non-root user, health-check, resource limits         |
| ✅ **124 unit tests**   | Full mock test suite + live integration tests, < 0.3 s                  |
| 🛠️ **Makefile**         | `make test`, `make lint`, `make docker-build` and more                  |
| 🔒 **No secrets**       | Zero external dependencies, no API keys                                 |

---

## Project Structure

```
ARD_MCP/
├── src/
│   └── ard_mcp/
│       ├── __init__.py      # Package metadata (__version__, __author__)
│       ├── config.py        # Environment-driven configuration
│       ├── client.py        # Async HTTP client (httpx) + error handling
│       ├── validators.py    # Domain constants + validate_ressort() helper
│       ├── formatters.py    # Markdown rendering of news items & channels
│       ├── tools.py         # MCP tool business logic
│       ├── resources.py     # MCP resource business logic
│       └── server.py        # FastMCP assembly + run() entry-point
├── tests/
│   ├── conftest.py          # Shared fixtures & mock payloads
│   ├── test_client.py       # Client unit + live integration tests
│   ├── test_formatters.py   # Formatter unit tests (pure functions)
│   ├── test_tools.py        # Tool unit + live integration tests
│   └── test_resources.py   # Resource unit + live integration tests
├── main.py                  # Thin entry-point (calls server.run())
├── pyproject.toml           # Project metadata, deps, pytest & pylint config
├── uv.lock                  # Locked dependency graph (commit this!)
├── Dockerfile               # Multi-stage production image
├── docker-compose.yml       # One-command remote deployment
├── .env.example             # Configuration template
├── Makefile                 # Developer shortcuts (test, lint, docker, clean)
├── CHANGELOG.md             # Version history
├── CONTRIBUTING.md          # How to contribute
└── README.md                # This file
```

---

## Quick Start — Local (Claude Desktop)

This mode uses `stdio` transport — the server is launched as a child process by Claude Desktop. No port is needed.

### Prerequisites

- macOS / Linux / Windows (WSL2)
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Claude Desktop](https://claude.ai/download)

### Step 1 — Clone and install

```bash
git clone https://github.com/Jakolo121/ard_mcp_server.git
cd ard_mcp_server

# Install all dependencies (uv creates .venv automatically)
uv sync
```

### Step 2 — Verify it works

```bash
uv run python -c "from ard_mcp.server import mcp; print('OK —', mcp.name)"
# Expected: OK — Tagesschau News API
```

### Step 3 — Connect Claude Desktop

Open your Claude Desktop config file:

| OS      | Path                                                              |
| ------- | ----------------------------------------------------------------- |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux   | `~/.config/Claude/claude_desktop_config.json`                     |

Add the following entry (adjust the path to your clone):

```json
{
  "mcpServers": {
    "tagesschau": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/ard_mcp_server",
        "run",
        "ard-mcp"
      ]
    }
  }
}
```

### Step 4 — Restart Claude Desktop

Quit and reopen Claude Desktop. You should see a 🔌 icon in the toolbar indicating the MCP server is connected.

### Step 5 — Try it!

Ask Claude:

> _"Was sind die aktuellen Tagesschau-Nachrichten?"_

---

## Remote / Docker Deployment

This mode uses `streamable_http` transport over HTTP. Ideal for servers, cloud VMs, or sharing the server across multiple clients. Stateless — no session state on the server, built for horizontal scaling.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+

### Step 1 — Create your .env file

```bash
cp .env.example .env
# Edit .env if you want a different port or log level
```

### Step 2 — Build and start

```bash
docker compose up --build -d
```

The server starts at `http://localhost:8000`.

### Step 3 — Verify health

```bash
docker compose logs ard-mcp      # view logs
docker compose ps                # check status
```

### Step 4 — Connect Claude Desktop (Streamable HTTP)

```json
{
  "mcpServers": {
    "tagesschau": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

> **Remote server?** Replace `localhost` with your server's IP or domain. Make sure port 8000 is open in your firewall.

### Stop / Update

```bash
docker compose down              # stop
docker compose up --build -d     # rebuild after code changes
```

---

## Configuration Reference

All settings are read from **environment variables** (or a `.env` file).

| Variable    | Default     | Description                                           |
| ----------- | ----------- | ----------------------------------------------------- |
| `TRANSPORT` | `stdio`     | Transport mode: `stdio` or `streamable_http`          |
| `HOST`      | `127.0.0.1` | Bind address (use `0.0.0.0` in Docker)                |
| `PORT`      | `8000`      | HTTP port (`streamable_http` only)                    |
| `LOG_LEVEL` | `INFO`      | Python log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Available Tools

These tools are callable by your AI assistant.

### `get_latest_news`

Get the top stories from the Tagesschau homepage.

| Parameter | Type | Default | Description         |
| --------- | ---- | ------- | ------------------- |
| `limit`   | int  | 10      | Max items to return |

---

### `get_news_by_ressort`

Filter news by category.

| Parameter | Type | Default | Description                                                             |
| --------- | ---- | ------- | ----------------------------------------------------------------------- |
| `ressort` | str  | —       | `inland` `ausland` `wirtschaft` `sport` `video` `investigativ` `wissen` |
| `limit`   | int  | 10      | Max items to return                                                     |

---

### `get_regional_news`

News from a specific German state.

| Parameter   | Type | Default | Description                                                                                                          |
| ----------- | ---- | ------- | -------------------------------------------------------------------------------------------------------------------- |
| `region_id` | int  | —       | 1=BW · 2=BY · 3=BE · 4=BB · 5=HB · 6=HH · 7=HE · 8=MV · 9=NI · 10=NW · 11=RP · 12=SL · 13=SN · 14=ST · 15=SH · 16=TH |
| `ressort`   | str  | None    | Optional category filter                                                                                             |
| `limit`     | int  | 10      | Max items to return                                                                                                  |

---

### `search_news`

Full-text search across all Tagesschau articles.

| Parameter     | Type | Default | Description               |
| ------------- | ---- | ------- | ------------------------- |
| `search_text` | str  | —       | Search query              |
| `page_size`   | int  | 10      | Results per page (max 30) |
| `result_page` | int  | 0       | Page offset (0-based)     |

---

### `get_news`

Flexible fetcher — combine region and category.

| Parameter | Type | Default | Description                |
| --------- | ---- | ------- | -------------------------- |
| `regions` | str  | None    | Region ID as string (1–16) |
| `ressort` | str  | None    | Category filter            |
| `limit`   | int  | 10      | Max items to return        |

---

### `get_channels`

List all live Tagesschau channels with stream URLs.

_(No parameters)_

---

## Available Resources

Resources are addressable URIs that MCP clients can read directly.

| URI                                 | Description                  |
| ----------------------------------- | ---------------------------- |
| `tagesschau://homepage`             | Homepage top stories         |
| `tagesschau://news/{ressort}`       | News by category             |
| `tagesschau://regional/{region_id}` | Regional news by state ID    |
| `tagesschau://search/{search_text}` | Search results               |
| `tagesschau://channels`             | Available channels & streams |

---

## Development Guide

### Setup

```bash
git clone https://github.com/Jakolo121/ard_mcp_server.git
cd ard_mcp_server

# Install with dev extras (pytest, pylint, etc.)
uv sync --extra dev
```

### Code organisation (SOLID)

Each module has exactly one responsibility:

| Module          | Responsibility                                         |
| --------------- | ------------------------------------------------------ |
| `config.py`     | Read & expose env vars                                 |
| `client.py`     | HTTP requests + error handling                         |
| `validators.py` | Domain constants (`VALID_RESSORTS`) + input validation |
| `formatters.py` | Turn raw API dicts into Markdown                       |
| `tools.py`      | Validate inputs, call client, call formatter           |
| `resources.py`  | Same as tools but for MCP resources                    |
| `server.py`     | Assemble FastMCP, register handlers, start             |

### Adding a new tool

1. Add a `tool_<name>()` async function in `tools.py`
2. Register it with `@mcp.tool()` in `server.py`
3. Write unit + integration tests in `tests/test_tools.py`

---

## Makefile Reference

```bash
make test          # fast unit tests (no network, ~0.3 s)
make test-all      # unit + live integration tests
make lint          # pylint (enforced at 10.00/10)
make check         # lint + unit tests — use as CI gate
make run           # start server in stdio mode (Claude Desktop)
make run-http      # start server in streamable_http mode
make docker-build  # build Docker image
make docker-run    # docker compose up -d
make docker-stop   # docker compose down
make docker-logs   # tail docker compose logs
make clean         # remove __pycache__, .pytest_cache, dist, etc.
```

---

## Running the Tests

### Unit tests (no internet required, fast)

```bash
uv run pytest                          # run all unit tests
uv run pytest -v                       # verbose output
uv run pytest tests/test_formatters.py # single file
```

### Live integration tests (requires internet)

```bash
uv run pytest -m integration           # all live tests
uv run pytest -m integration -v        # verbose
```

### Full suite

```bash
uv run pytest -m ""                    # unit + integration
```

### Expected results

```
124 passed in 0.28s   ← unit tests (no network)
 23 selected          ← integration tests (live API)
```

---

## Troubleshooting

### Claude Desktop shows no MCP tools

1. Check that the `claude_desktop_config.json` path is **absolute**
2. Run `uv run python main.py` in the terminal — it should start without errors
3. Fully quit and reopen Claude Desktop (Cmd+Q, not just close window)

### Docker container exits immediately

```bash
docker compose logs ard-mcp
```

Common causes: wrong `TRANSPORT` value (must be `streamable_http` in Docker), port already in use.

### API timeouts

The Tagesschau API occasionally rate-limits certain filtered endpoints. This is normal — the server returns a descriptive error message rather than crashing. Retry after a few seconds.

### Import errors in tests

```bash
uv sync --extra dev     # ensure dev deps are installed
uv run pytest           # always run via uv, not bare pytest
```

---

## License

This project is provided as-is under the MIT License.  
News content belongs to ARD / Tagesschau — public broadcasting data, for personal / research use.
