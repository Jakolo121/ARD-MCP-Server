#!/usr/bin/env python3
"""Bump the project version across pyproject.toml and server.json.

Usage: uv run scripts/bump_version.py <new-version>
Example: uv run scripts/bump_version.py 2.1.0
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
SERVER_JSON = ROOT / "server.json"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def bump_pyproject(new_version: str) -> str:
    text = PYPROJECT.read_text()
    old_match = re.search(r'^version = "([^"]+)"', text, flags=re.MULTILINE)
    if not old_match:
        raise SystemExit(f"Could not find version field in {PYPROJECT}")
    old_version = old_match.group(1)
    text = re.sub(
        r'^version = "[^"]+"',
        f'version = "{new_version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(text)
    return old_version


def bump_server_json(new_version: str) -> str:
    data = json.loads(SERVER_JSON.read_text())
    old_version = data["version"]
    data["version"] = new_version
    for package in data.get("packages", []):
        package["version"] = new_version
    SERVER_JSON.write_text(json.dumps(data, indent=2) + "\n")
    return old_version


def main() -> None:
    if len(sys.argv) != 2 or not VERSION_RE.match(sys.argv[1]):
        raise SystemExit("Usage: bump_version.py <new-version>  (e.g. 2.1.0)")

    new_version = sys.argv[1]

    old_pyproject = bump_pyproject(new_version)
    old_server_json = bump_server_json(new_version)

    print(f"pyproject.toml: {old_pyproject} -> {new_version}")
    print(f"server.json:    {old_server_json} -> {new_version}")
    print()
    print("Next steps:")
    print("  git add pyproject.toml server.json")
    print(f'  git commit -m "chore: bump version to {new_version}"')
    print(f"  git tag v{new_version}")
    print(f"  git push origin main v{new_version}")


if __name__ == "__main__":
    main()
