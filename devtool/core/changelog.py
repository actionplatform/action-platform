"""CHANGELOG generation from conventional commits."""

from __future__ import annotations

import re
from datetime import date

TYPE_RE = re.compile(
    r"^(?::\w+:\s*)?(?P<type>feat|fix|chore|docs|refactor|test|perf|build|ci|style)"
    r"(?:\([^)]+\))?:\s*(?P<msg>.+)$",
    re.IGNORECASE,
)

SECTIONS = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactor",
    "docs": "Docs",
    "test": "Tests",
    "build": "Build",
    "ci": "CI",
    "chore": "Chore",
    "style": "Style",
}


def render(version: str, commits: list[str]) -> str:
    buckets: dict[str, list[str]] = {}
    for line in commits:
        match = TYPE_RE.match(line)
        if not match:
            continue
        buckets.setdefault(match.group("type").lower(), []).append(match.group("msg"))

    lines = [f"## v{version} — {date.today().isoformat()}", ""]
    for key, title in SECTIONS.items():
        items = buckets.get(key)
        if not items:
            continue
        lines.append(f"### {title}")
        lines.extend(f"- {msg}" for msg in items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
