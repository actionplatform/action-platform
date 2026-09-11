"""CHANGELOG generation from icon-typed commits."""

from __future__ import annotations

import re
from datetime import date

TYPE_RE = re.compile(
    r"^(?:\S+\s+)?(?P<type>FEATURE|PEP8|ISSUE|BUG|DOCS|PyPI|TEST|CI/CD|SECURITY)"
    r":\s*(?P<msg>.+)$",
    re.IGNORECASE,
)

SECTIONS: dict[str, str] = {
    "feature": "Features",
    "bug": "Bug Fixes",
    "security": "Security",
    "pypi": "Release",
    "docs": "Docs",
    "test": "Tests",
    "ci/cd": "CI/CD",
    "pep8": "Style",
    "issue": "Issues",
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
