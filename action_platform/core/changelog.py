"""CHANGELOG generation from Conventional Commits (https://www.conventionalcommits.org/en/v1.0.0/)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

COMMIT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<msg>.+)$"
)

SECTIONS: dict[str, str] = {
    "breaking": "Breaking Changes",
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Docs",
    "test": "Tests",
    "build": "Build",
    "ci": "CI",
    "style": "Style",
    "chore": "Chores",
    "revert": "Reverts",
}


def render(version: str, commits: list[str]) -> str:
    buckets: dict[str, list[str]] = {}

    for line in commits:
        match = COMMIT_RE.match(line)

        if not match:
            continue

        key = "breaking" if match.group("bang") else match.group("type")
        scope = match.group("scope")
        msg = f"**{scope}:** {match.group('msg')}" if scope else match.group("msg")
        buckets.setdefault(key, []).append(msg)

    lines = [f"## v{version} — {date.today().isoformat()}", ""]

    for key, title in SECTIONS.items():
        items = buckets.get(key)

        if not items:
            continue

        lines.append(f"### {title}")
        lines.extend(f"- {msg}" for msg in items)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


HEADER = "# Changelog\n"


def prepend(path: Path, entry: str) -> None:
    """Insert the release entry at the top; older releases stay below."""
    previous = path.read_text() if path.exists() else ""

    if previous.startswith(HEADER):
        previous = previous[len(HEADER) :].lstrip("\n")

    body = entry.rstrip("\n") + "\n"

    if previous.strip():
        body += "\n" + previous.rstrip("\n") + "\n"

    path.write_text(HEADER + "\n" + body)
