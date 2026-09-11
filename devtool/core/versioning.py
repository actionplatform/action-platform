"""Semver bump + LAST_VERSION management."""

from __future__ import annotations

import re
from pathlib import Path

from devtool.core.exception import DevtoolError

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([\w.]+))?$")


def parse(version: str) -> tuple[int, int, int, str | None]:
    match = SEMVER_RE.match(version.strip().lstrip("v"))
    if not match:
        raise DevtoolError(f"Invalid semver: {version!r}")
    major, minor, patch, pre = match.groups()
    return int(major), int(minor), int(patch), pre


def format(major: int, minor: int, patch: int, pre: str | None = None) -> str:
    base = f"{major}.{minor}.{patch}"
    return f"{base}-{pre}" if pre else base


def bump(version: str, level: str) -> str:
    major, minor, patch, _ = parse(version)
    if level == "major":
        return format(major + 1, 0, 0)
    if level == "minor":
        return format(major, minor + 1, 0)
    if level == "patch":
        return format(major, minor, patch + 1)
    parse(level)
    return level


def read(path: Path) -> str:
    return path.read_text().strip() if path.exists() else "0.0.0"


def write(path: Path, version: str) -> None:
    path.write_text(f"{version}\n")
