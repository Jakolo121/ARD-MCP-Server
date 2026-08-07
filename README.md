# German Newsfeed MCP Server

<!-- mcp-name: io.github.jakolo121/german-newsfeed-mcp -->

![pylint](https://img.shields.io/badge/pylint-9.97%2F10-brightgreen)
![tests](https://img.shields.io/badge/tests-181%20passed-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-Apache%202.0-blue)

> **Disclaimer:** This is a private, unofficial project. It is not an ARD
> product and is neither operated nor endorsed by ARD,
> ARD-aktuell, or NDR. It is developed independently of the author's
> professional employment. "ARD" and "tagesschau" are trademarks of their
> respective owners and are named here solely to describe the API being
> accessed.

> This project merely connects the public API to an MCP-capable AI
> assistant. ARD-aktuell is responsible for the API itself, its
> operation, and its content; this project cannot provide information
> on any of those. Please raise any concerns about this project, in
> particular from rights holders, as a
> [GitHub issue](https://github.com/Jakolo121/german-newsfeed-mcp/issues).
> Substantiated concerns will be addressed promptly.

## In thirty seconds

This [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server
connects your AI assistant (Claude Desktop and others) to the public news
API of tagesschau.de: current headlines, category and regional news, and
full-text search, locally via `stdio`, no API key required.

Example: asked _"Was sind die aktuellen Schlagzeilen?"_, the assistant
answers with the current top stories from tagesschau.de, each with title,
date, summary, and a link to the article.

Language:

- 🇩🇪 [Deutsch](README.md)
- 🇬🇧 English

---

<details>
<summary><strong>Table of Contents</strong></summary>

1. [What is this?](#what-is-this)
2. [Data Source and Terms of Use](#data-source-and-terms-of-use)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Quick Start Local (Claude Desktop)](#quick-start-local-claude-desktop)
6. [Remote / Docker Deployment](#remote--docker-deployment)
7. [Configuration Reference](#configuration-reference)
8. [Available Tools](#available-tools)
9. [Available Resources](#available-resources)
10. [Development Guide](#development-guide)
11. [Running the Tests](#running-the-tests)
12. [Makefile Reference](#makefile-reference)
13. [Troubleshooting](#troubleshooting)
14. [When it stops working](#when-it-stops-working)
15. [License & Acknowledgements](#license--acknowledgements)

</details>

---

## What is this?

This MCP server connects the public news API of tagesschau.de to your AI assistant (Claude, Open Claw, etc.).

Once connected, your AI can answer questions like:

- _"Was sind die aktuellen Schlagzeilen?"_
- _"Zeig mir die neuesten Wirtschaftsnachrichten."_
- _"Suche nach Artikeln über Ukraine."_
- _"Welche Regionalnachrichten gibt es aus Bayern?"_

For details on the API and its terms, see [Data Source and Terms of Use](#data-source-and-terms-of-use). No API key required.

---

## Data Source and Terms of Use

This server calls the publicly accessible endpoint
`www.tagesschau.de/api2u/`, operated by ARD-aktuell. The delivered
content originates from the ARD broadcasters, remains subject to their
rights and to the terms of use of tagesschau.de:
https://www.tagesschau.de/nutzungsbedingungen/

The API is not officially documented. Community documentation is
available at bund.dev (https://tagesschau.api.bund.dev). bund.dev is a
civil-society documentation project, neither the operator of the API
nor a rights holder of the content. Its documentation served as a
reference for this project but does not grant any usage rights.

Applicable limits: at most 60 requests per hour, and no republication
of the content except for offerings under a CC licence
(https://tagesschau.de/creativecommons). Compliance is the
responsibility of whoever operates a given instance.

The robots.txt of tagesschau.de additionally declares an express
reservation of rights under Section 44b(3) of the German Copyright Act
(as of 2026-05-19): text and data mining and the automated use of the
content for training or fine-tuning AI models are prohibited without
written consent. Expressly exempt is automated access for the sole
purpose of retrieval-augmented generation (RAG) or grounding, provided
the technical directives of the robots.txt are complied with and the
content remains attributed to its original source. This server falls
under that exemption: it passes content to the assistant exclusively
together with source links. The retrieved content must not be used to
train AI models.

---

## Features

|                         |                                                                         |
| ----------------------- | ----------------------------------------------------------------------- |
| 🗞️ **Live news**        | Fetches breaking news, categorised news, and regional news in real time |
| 🔍 **Full-text search** | Search across all available articles                                    |
| 📺 **Live streams**     | List all available channels and HLS stream URLs                         |
| ⏱️ **Rate limiter**     | Local token bucket honouring the API's 60/h limit                       |
| 🚀 **Dual transport**   | `stdio` for local Claude Desktop; `streamable-http` for remote / Docker |
| 🐳 **Docker-ready**     | Multi-stage image, non-root user, health-check, resource limits         |
| ✅ **181 tests**        | 160 unit tests + 21 live integration tests                              |
| 🛠️ **Makefile**         | `make test`, `make lint`, `make docker-build` and more                  |
| 🔒 **No secrets**       | Public API, no API keys                                                 |

---

## Project Structure

```
german-newsfeed-mcp/
├── src/
│   └── german_newsfeed_mcp/
│       ├── __init__.py      # Package metadata
│       ├── config.py        # Environment-driven configuration
│       ├── client.py        # Async HTTP client (httpx) + error handling
│       ├── rate_limiter.py  # Token-bucket rate limiter
│       ├── validators.py    # Domain constants + validation helpers
│       ├── formatters.py    # Markdown rendering of news items & channels
│       ├── tools.py         # MCP tool business logic
│       ├── resources.py     # MCP resource business logic
│       └── server.py        # Composition root: FastMCP + run() entry-point
├── tests/
│   ├── conftest.py          # Shared fixtures & mock payloads
│   ├── test_client.py       # Client unit + live integration tests
│   ├── test_rate_limiter.py # Rate-limiter unit tests
│   ├── test_formatters.py   # Formatter unit tests (pure functions)
│   ├── test_tools.py        # Tool unit + live integration tests
│   └── test_resources.py    # Resource unit + live integration tests
├── main.py                  # Thin entry-point (calls server.run())
├── pyproject.toml           # Project metadata, deps, pytest & pylint config
├── uv.lock                  # Locked dependency graph (commit this!)
├── Dockerfile               # Multi-stage production image
├── docker-compose.yml       # One-command remote deployment
├── .env.example             # Configuration template
├── Makefile                 # Developer shortcuts (test, lint, docker, clean)
├── CHANGELOG.md             # Version history
├── CONTRIBUTING.md          # How to contribute
└── README.md                # German version of this file
```

---

## Quick Start Local (Claude Desktop)

Also applicable to other AI assistants, edit their respective config instead. This mode uses `stdio` transport; the server is launched as a child process. No port is needed.

### Prerequisites

- macOS / Linux / Windows (WSL2)
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Claude Desktop](https://claude.ai/download)

### Step 1: Clone and install

```bash
git clone https://github.com/Jakolo121/german-newsfeed-mcp.git
cd german-newsfeed-mcp
uv sync
```

### Step 2: Verify it works

```bash
uv run python -c "from german_newsfeed_mcp.server import mcp; print('OK!', mcp.name)"
# Expected: OK! German Newsfeed MCP
```

### Step 3: Connect Claude Desktop

Open your Claude Desktop config file:

| OS      | Path                                                              |
| ------- | ----------------------------------------------------------------- |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux   | `~/.config/Claude/claude_desktop_config.json`                     |

Add the following entry (adjust the path to your clone):

```json
    "german-newsfeed": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/german-newsfeed-mcp",
        "run",
        "german-newsfeed-mcp"
      ]
    },
```

### Step 4: Restart Claude Desktop

Quit and reopen the application, or reload its MCP servers, depending on the application.

### Step 5: Try it!

Ask your assistant:

> _"Was sind die aktuellen Nachrichten?"_

---

## Remote / Docker Deployment

Self-hosting for your own or team-internal use. The recommended default
is `stdio` (see [Quick Start](#quick-start-local-claude-desktop));
the `streamable-http` transport is an option you choose deliberately.

**Security note:** The HTTP transport has no authentication. Do not
expose it publicly without an authentication layer in front (e.g. a
reverse proxy). The Compose setup therefore deliberately binds the port
to `127.0.0.1` only. Whoever makes an instance reachable for third
parties becomes the responsible operator under the
[terms of use](#data-source-and-terms-of-use).

**Rate limiter limitations:** `stateless_http=True` refers to MCP
sessions, not to the rate limiter. The token bucket is process-local
in-memory state. Two limitations follow:

1. Multiple replicas against the same upstream API multiply the request
   budget.
2. A container restart resets the bucket to full. Combined with
   `restart: unless-stopped` and a crash loop, this can exceed the
   limit. Watch the logs.

(The legacy `sse` transport is still supported.)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+

### Step 1: Create your .env file

```bash
cp .env.example .env
# Edit .env if you want a different port or log level
```

### Step 2: Build and start

```bash
docker compose up --build -d
```

Or:

```bash
make docker-build
make docker-run
```

The server starts at `http://localhost:8000`.

### Step 3: Verify health

```bash
docker compose logs german-newsfeed-mcp
docker compose ps
```

Or:

```bash
make docker-logs
```

### Step 4: Connect Claude Desktop (Streamable HTTP)

```json
    "german-newsfeed": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    },
```

For external servers: put an authentication layer in front first (see the security note above), then adjust the loopback binding in `docker-compose.yml` and replace `localhost` with your proxy's address.

### Stop / Update

```bash
docker compose down
docker compose up --build -d
```

---

## Configuration Reference

All settings are read from environment variables (or a `.env` file).

| Variable              | Default   | Description                                                         |
| --------------------- | --------- | ------------------------------------------------------------------- |
| `TRANSPORT`           | `stdio`   | `stdio` or `streamable-http` (`sse` legacy)                         |
| `HOST`                | `0.0.0.0` | Bind address (HTTP transports only)                                 |
| `PORT`                | `4200`    | HTTP port (HTTP transports only)                                    |
| `LOG_LEVEL`           | `INFO`    | DEBUG, INFO, WARNING, ERROR                                         |
| `RATE_LIMIT_PER_HOUR` | `60`      | Local request budget per hour towards the upstream API              |
| `USER_AGENT_CONTACT`  | —         | Optional: contact info in the User-Agent header; omitted when unset |

The defaults apply when running directly (`uv run german-newsfeed-mcp`).
The Compose setup overrides them: it sets `HOST=0.0.0.0` and `PORT=8000`
(see `docker-compose.yml`).

---

## Available Tools

These tools are callable by your AI assistant.

### `get_latest_news`

Get the top stories.

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

> Ressort strings are automatically normalised to lowercase: `"Inland"`, `"INLAND"` and `"inland"` are all equivalent.

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

Full-text search across all available articles.

| Parameter     | Type | Default | Description               |
| ------------- | ---- | ------- | ------------------------- |
| `search_text` | str  | —       | Search query              |
| `page_size`   | int  | 10      | Results per page (max 30) |
| `result_page` | int  | 0       | Page offset (0-based)     |

---

### `get_channels`

List all live channels with stream URLs.

_(No parameters)_

---

## Available Resources

Resources are addressable URIs that MCP clients can read directly.

| URI                                      | Description                  |
| ---------------------------------------- | ---------------------------- |
| `news://tagesschau/homepage`             | Homepage top stories         |
| `news://tagesschau/news/{ressort}`       | News by category             |
| `news://tagesschau/regional/{region_id}` | Regional news by state ID    |
| `news://tagesschau/search/{search_text}` | Search results               |
| `news://tagesschau/channels`             | Available channels & streams |

---

## Development Guide

### Setup

```bash
git clone https://github.com/Jakolo121/german-newsfeed-mcp.git
cd german-newsfeed-mcp
uv sync --extra dev
```

Start the server:

```bash
uv run german-newsfeed-mcp
```

Or:

```bash
make run
```

### Code organisation (SOLID)

Each module has exactly one responsibility:

| Module            | Responsibility                                               |
| ----------------- | ------------------------------------------------------------ |
| `config.py`       | Read & expose env vars                                       |
| `client.py`       | HTTP requests + error handling                               |
| `rate_limiter.py` | Local request budget (token bucket)                          |
| `validators.py`   | Domain constants (`VALID_RESSORTS`) + input validation       |
| `formatters.py`   | Turn raw API dicts into Markdown                             |
| `tools.py`        | Validate inputs, call client, call formatter                 |
| `resources.py`    | Same as tools but for MCP resources                          |
| `server.py`       | Composition root: assemble FastMCP, register handlers, start |

### Adding a new tool

1. Add a `tool_<name>()` async function in `tools.py`
2. Register it with `@mcp.tool()` in `server.py`
3. Write unit + integration tests in `tests/test_tools.py`

---

## Running the Tests

### Unit tests (no internet required, fast)

```bash
uv run pytest -m "not integration"     # run all unit tests
uv run pytest -m "not integration" -v  # verbose output
uv run pytest tests/test_formatters.py # single file
```

Or:

```bash
make test
```

### Live integration tests (requires internet)

```bash
uv run pytest -m integration           # all live tests
uv run pytest -m integration -v        # verbose
```

### Full suite

```bash
uv run pytest
```

Or:

```bash
make test-all
```

### Quality gate (lint + tests)

```bash
uv run pylint src/german_newsfeed_mcp/
uv run pytest
```

Or:

```bash
make check
```

### Expected results

```
160 passed            ← unit tests (no network)
 21 selected          ← integration tests (live API)
```

---

## Makefile Reference

```bash
make test          # fast unit tests (no network, ~0.3 s)
make test-all      # unit + live integration tests
make lint          # pylint
make check         # lint + unit tests — use as CI gate
make run           # start server in stdio mode (Claude Desktop)
make run-http      # start server in streamable-http mode
make docker-build  # build Docker image
make docker-run    # docker compose up -d
make docker-stop   # docker compose down
make docker-logs   # tail docker compose logs
make clean         # remove __pycache__, .pytest_cache, dist, etc.
```

---

## Troubleshooting

### Claude Desktop shows no MCP tools

1. Check that the `claude_desktop_config.json` path is **absolute**
2. Run `uv run python main.py` in the terminal, it should start without errors
3. Fully quit and reopen Claude Desktop (Cmd+Q, not just close window)

### Docker container exits immediately

```bash
docker compose logs german-newsfeed-mcp
```

Or:

```bash
make docker-logs
```

Common causes: wrong `TRANSPORT` value (must be `streamable-http` in Docker), port already in use.

### API timeouts

The upstream API occasionally rate-limits certain endpoints. This is normal, the server returns a descriptive error message rather than crashing. Retry after a few seconds.

### Rate-limit errors

If the server reports "Rate limit exceeded", the local request budget (`RATE_LIMIT_PER_HOUR`, default 60/h) is exhausted. No request was sent upstream. Try again later.

### Import errors in tests

```bash
uv sync --extra dev     # ensure dev deps are installed
uv run pytest           # always run via uv, not bare pytest
```

---

## When it stops working

The upstream API is not officially documented and can change without
notice. You can tell by the tools suddenly returning empty lists or
error messages although tagesschau.de is reachable, and by the live
integration tests failing (`uv run pytest tests/ -m integration`).

All endpoints are defined in a single place: `ENDPOINTS` in
`src/german_newsfeed_mcp/client.py`. API changes can be tracked there.

The CI job `upstream-check` (`.github/workflows/ci.yml`) runs exactly
these live tests weekly against the real API and fails loudly when the
response format no longer matches.

---

## License & Acknowledgements

Apache License 2.0.

The delivered news items are content of the ARD broadcasters, subject to their rights and the terms of use of tagesschau.de, see [Data Source and Terms of Use](#data-source-and-terms-of-use).

Thanks to **[AndreasFischer1985](https://github.com/AndreasFischer1985)**, the bund.dev community for documenting the API and above all to the journalists at the ARD broadcasters, whose work this project merely passes along.
