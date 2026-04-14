# ARD / Tagesschau MCP Server

> Verbinde deinen KI-Assistenten direkt mit aktuellen Nachrichten.  
> Ein produktionsreifer [Model Context Protocol (MCP)](https://modelcontextprotocol.io)-Server, der die öffentliche Tagesschau-API nutzt.

![pylint](https://img.shields.io/badge/pylint-10.00%2F10-brightgreen)
![tests](https://img.shields.io/badge/tests-124%20passed-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-Apache%202.0-blue)

Sprache:

- 🇩🇪 Deutsch
- 🇬🇧 [English](README_en.md)

---

## Inhaltsverzeichnis

1. [Was ist dieses Projekt?](#was-ist-dieses-Projekt)
2. [Features](#features)
3. [Projektstruktur](#projektstruktur)
4. [Schnellstart Lokal (Claude Desktop)](#schnellstart--lokal-claude-desktop)
5. [Remote / Docker-Deployment](#remote--docker-deployment)
6. [Konfigurationsreferenz](#konfigurationsreferenz)
7. [Verfügbare Tools](#verfügbare-tools)
8. [Verfügbare Ressourcen](#verfügbare-ressourcen)
9. [Entwicklung](#entwicklung)
10. [Tests](#tests)
11. [Makefile-Referenz](#makefile-referenz)
12. [Fehlerbehebung](#fehlerbehebung)
13. [Lizenz & Danksagung](#lizenz--danksagung)

---

## Was ist dieses Projekt?

Dieser MCP-Server verbindet die ARD/Tagesschau-API mit deinem KI-Assistenten (Claude, Open Claw u.a.).

Sobald verbunden, kann der Assistent z.B folgende Anfragen beantworten:

- _„Was sind die aktuellen Schlagzeilen?"_
- _„Zeig mir die neuesten Wirtschaftsnachrichten."_
- _„Suche nach Artikeln über Ukraine."_
- _„Welche Regionalnachrichten gibt es aus Bayern?"_

Die API stammt von [Tagesschau](https://tagesschau.api.bund.dev).

---

## Features

|                      |                                                           |
| -------------------- | --------------------------------------------------------- |
| **Live-Nachrichten** | Aktuelle Meldungen, kategorisiert, regional, in Echtzeit  |
| **Volltextsuche**    | Über alle verfügbaren Artikel                             |
| **Livestreams**      | Alle Tagesschau-Kanäle mit HLS-URLs                       |
| **Dual-Transport**   | `stdio` lokal; `streamable_http` für Remote und Docker    |
| **Docker**           | Multi-Stage-Build, Nicht-Root-User, Health-Checks, Limits |
| **124 Tests**        | Unit-Tests (< 0,3 s) + Live-Integrationstests             |
| **Makefile**         | `make test`, `make lint`, `make docker-build`             |
| **Keine Secrets**    | Öffentliche API, kein API-Schlüssel nötig                 |

---

## Projektstruktur

```
ARD_MCP/
├── src/
│   └── ard_mcp/
│       ├── __init__.py      # Paket-Metadaten
│       ├── config.py        # Umgebungsvariablen
│       ├── client.py        # Async HTTP (httpx) + Fehlerbehandlung
│       ├── validators.py    # Validierung
│       ├── formatters.py    # Markdown-Output
│       ├── tools.py         # MCP-Tool-Logik
│       ├── resources.py     # MCP-Ressourcen-Logik
│       └── server.py        # FastMCP + run()
├── tests/
│   ├── conftest.py          # Fixtures, Mock-Daten
│   ├── test_client.py       # Client-Tests
│   ├── test_formatters.py   # Formatter-Tests
│   ├── test_tools.py        # Tool-Tests
│   └── test_resources.py    # Ressourcen-Tests
├── main.py                  # Einstiegspunkt
├── pyproject.toml           # Abhängigkeiten, Config
├── uv.lock                  # Dependency-Lock
├── Dockerfile               # Produktions-Image
├── docker-compose.yml       # Docker-Deployment
├── .env.example             # Konfigurationsvorlage
├── Makefile                 # Entwickler-Tools
├── CHANGELOG.md             # Versionshistorie
├── CONTRIBUTING.md          # Beiträge
└── README.md                # Diese Datei
```

---

## Schnellstart Lokal (Bsp. Claude Desktop - gilt aber auch für andere KI-Assistenten)

Der `stdio`-Transport startet den Server als Subprocess. Es muss kein Port angegeben werden.

### Voraussetzungen

- macOS / Linux / Windows (WSL2)
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Claude Desktop](https://claude.ai/download)

### Schritt 1: Repository klonen und Projekt installieren

```bash
git clone https://github.com/Jakolo121/ard_mcp_server.git
cd ard_mcp_server
uv sync
```

### Schritt 2: Funktionscheck

```bash
uv run python -c "from ard_mcp.server import mcp; print('OK!', mcp.name)"
# Erwartete Ausgabe: OK! Tagesschau News API
```

### Schritt 3: Claude Desktop oder andern Aissistenten konfigurieren

**Wir nehmen hier Claude Desktop als Beispiel, bei anderen Assistenten die entsprechende Konfig bearbeiten**

Öffne die Claude-Konfigurationsdatei:

| Betriebssystem | Pfad                                                              |
| -------------- | ----------------------------------------------------------------- |
| macOS          | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows        | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux          | `~/.config/Claude/claude_desktop_config.json`                     |

Eintrag hinzufügen (Pfad anpassen):

```json
    "tagesschau": {
      "command": "uv",
      "args": [
        "--directory",
        "/absoluter/pfad/zu/ard_mcp_server",
        "run",
        "ard-mcp"
      ]
    },
```

### Schritt 4: Application neu starten

Die Application neustarten oder die MCP-Server neu laden, je nach Application

### Schritt 5: Test

Frage KI-Assistenten:

> _„Was sind die aktuellen Tagesschau-Nachrichten?"_

---

## Remote / Docker-Deployment

Der `streamable_http`-Transport nutzt HTTP. Geeignet für Server, Cloud-VMs oder Multi-Client-Setup. Stateless! Legacy sse wird noch supportet!

### Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+

### Schritt 1: .env erstellen/kopieren

```bash
cp .env.example .env
# Bei Bedarf editieren (Port, Log-Level etc.)
```

### Schritt 2: Bauen und starten

```bash
docker compose up --build -d
```

Oder:

```bash
make docker-build
make docker-run
```

Der Server läuft auf `http://localhost:8000`.

### Schritt 3: Status prüfen

```bash
docker compose logs ard-mcp
docker compose ps
```

Oder:

```bash
make docker-logs
```

### Schritt 4: Claude Desktop anpassen (Streamable HTTP)

```json
    "tagesschau": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    },
```

Für externe Server: `localhost` durch IP oder Domain ersetzen, Port 8000 freigeben.

### Stoppen / Aktualisieren

```bash
docker compose down
docker compose up --build -d
```

---

## Konfigurationsreferenz

Alle Einstellungen kommen aus Umgebungsvariablen oder `.env`.

| Variable    | Standard | Beschreibung                      |
| ----------- | -------- | --------------------------------- |
| `TRANSPORT` | `stdio`  | `stdio` oder `streamable_http`    |
| `PORT`      | `8000`   | HTTP-Port (nur `streamable_http`) |
| `LOG_LEVEL` | `INFO`   | DEBUG, INFO, WARNING, ERROR       |

---

## Verfügbare Tools

Dein Assistent kann diese aufrufen.

### `get_latest_news`

Top-Meldungen abrufen.

| Parameter | Typ | Standard | Beschreibung        |
| --------- | --- | -------- | ------------------- |
| `limit`   | int | 10       | Maximale Ergebnisse |

---

### `get_news_by_ressort`

Nach Kategorie filtern.

| Parameter | Typ | Standard | Beschreibung                                                            |
| --------- | --- | -------- | ----------------------------------------------------------------------- |
| `ressort` | str | —        | `inland` `ausland` `wirtschaft` `sport` `video` `investigativ` `wissen` |
| `limit`   | int | 10       | Maximale Ergebnisse                                                     |

> Ressort-Strings werden automatisch zu Kleinbuchstaben normalisiert — `"Inland"`, `"INLAND"` und `"inland"` sind gleichwertig.

---

### `get_regional_news`

Regionalnachrichten.

| Parameter   | Typ | Standard | Beschreibung                                                                                                           |
| ----------- | --- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `region_id` | int | —        | 1=BW · 2=BY · 3=BE · 4=BB · 5=HB · 6=HH · 7=HE · 8=MV · 9=NI · 10=NRW · 11=RLP · 12=SL · 13=SN · 14=ST · 15=SH · 16=TH |
| `ressort`   | str | None     | Optionaler Kategorie-Filter                                                                                            |
| `limit`     | int | 10       | Maximale Ergebnisse                                                                                                    |

---

### `search_news`

Volltextsuche.

| Parameter     | Typ | Standard | Beschreibung                  |
| ------------- | --- | -------- | ----------------------------- |
| `search_text` | str | —        | Suchanfrage                   |
| `page_size`   | int | 10       | Ergebnisse pro Seite (max 30) |
| `result_page` | int | 0        | Seitenversatz (0-basiert)     |

---

### `get_news`

Kombinierte Abfrage — Region + Kategorie.

| Parameter | Typ | Standard | Beschreibung        |
| --------- | --- | -------- | ------------------- |
| `regions` | str | None     | Region-ID (1–16)    |
| `ressort` | str | None     | Kategorie-Filter    |
| `limit`   | int | 10       | Maximale Ergebnisse |

---

### `get_channels`

Live-Kanäle mit Stream-URLs.

_(Keine Parameter)_

---

## Verfügbare Ressourcen

URIs, die MCP-Clients lesen können.

| URI                                 | Beschreibung               |
| ----------------------------------- | -------------------------- |
| `tagesschau://homepage`             | Top-Meldungen              |
| `tagesschau://news/{ressort}`       | Nachrichten nach Kategorie |
| `tagesschau://regional/{region_id}` | Regionalnachrichten        |
| `tagesschau://search/{search_text}` | Suchergebnisse             |
| `tagesschau://channels`             | Kanäle & Streams           |

---

## Entwicklung

### Setup

```bash
git clone https://github.com/Jakolo121/ard_mcp_server.git
cd ard_mcp_server
uv sync --extra dev
```

Server starten:

```bash
uv run ard-mcp
```

Oder:

```bash
make run
```

### Code-Struktur (SOLID)

Jedes Modul hat eine Aufgabe:

| Modul           | Aufgabe                                        |
| --------------- | ---------------------------------------------- |
| `config.py`     | Umgebungsvariablen lesen                       |
| `client.py`     | HTTP + Fehlerbehandlung                        |
| `validators.py` | Eingabevalidierung                             |
| `formatters.py` | API-Dicts zu Markdown                          |
| `tools.py`      | Tool-Logik (validieren, aufrufen, formatieren) |
| `resources.py`  | Ressourcen-Logik                               |
| `server.py`     | FastMCP, Handler, Startup                      |

### Neues Tool

1. Funktion in `tools.py` hinzufügen
2. Mit `@mcp.tool()` in `server.py` registrieren
3. Tests in `tests/test_tools.py` schreiben

---

## Tests

### Unit-Tests (schnell, kein Netz)

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/test_formatters.py
```

Oder:

```bash
make test
```

### Live-Tests (braucht Internet)

```bash
uv run pytest -m integration
uv run pytest -m integration -v
```

### Alle Tests

```bash
uv run pytest -m ""
```

Oder:

```bash
make test-all
```

### Qualität checken (Lint + Tests)

```bash
uv run pylint src/ard_mcp/
uv run pytest
```

Oder:

```bash
make check
```

### Erwartete Ergebnisse

```
124 passed in X s   ← Unit-Tests
 23 selected          ← Integrationstests
```

---

## Makefile-Referenz

```bash
make test          # Unit-Tests (~0,3 s)
make test-all      # Unit- + Integrationstests
make lint          # pylint
make check         # lint + Tests (für CI)
make run           # stdio-Server
make run-http      # HTTP-Server
make docker-build  # Docker bauen
make docker-run    # docker compose up
make docker-stop   # docker compose down
make docker-logs   # Logs folgen
make clean         # __pycache__ etc. löschen
```

---

## Fehlerbehebung

### Claude Desktop zeigt keine Tools

1. Pfad in `claude_desktop_config.json` ist absolut?
2. `uv run python main.py` startet fehlerlos?
3. Claude komplett beenden, neu öffnen (Cmd+Q, nicht einfach fenster schließen)

### Docker-Container beendet sich sofort

```bash
docker compose logs ard-mcp
```

Oder:

```bash
make docker-logs
```

Häufig: falscher `TRANSPORT` (in Docker muss es `streamable_http` sein), oder Port belegt.

### API-Timeouts

Die Tagesschau-API limitiert manchmal. Das ist normal, der Server meldet einen Fehler, statt abzustürzen. Später nochmal versuchen.

### Import-Fehler bei Tests

```bash
uv sync --extra dev
uv run pytest
```

(Nicht bare `pytest` verwenden)

---

## Lizenz & Danksagung

Apache License 2.0.

Nachrichteninhalte: ARD / Tagesschau öffentliche Rundfunkdaten, persönliche Nutzung und Forschung.

Danke an **[AndreasFischer1985](https://github.com/AndreasFischer1985)** für die [Tagesschau-API](https://tagesschau.api.bund.dev).
