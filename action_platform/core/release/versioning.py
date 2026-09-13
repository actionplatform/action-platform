"""Semver bump + LAST_VERSION management."""

from __future__ import annotations

import re
from pathlib import Path

from action_platform.core.exception import ActionPlatformError

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([\w.]+))?$")


def parse(version: str) -> tuple[int, int, int, str | None]:
    match = SEMVER_RE.match(version.strip().lstrip("v"))
    if not match:
        raise ActionPlatformError(f"Invalid semver: {version!r}")
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


def strip_pre(version: str) -> str:
    major, minor, patch, _ = parse(version)

    return format(major, minor, patch)


def next_rc(base: str, existing_tags: list[str]) -> str:
    """`base` plus the next -rc.N not yet tagged."""
    prefix = f"v{base}-rc."
    taken = [
        int(t[len(prefix) :])
        for t in existing_tags
        if t.startswith(prefix) and t[len(prefix) :].isdigit()
    ]

    return f"{base}-rc.{max(taken, default=0) + 1}"


def read(path: Path) -> str:
    return path.read_text().strip() if path.exists() else "0.0.0"


def write(path: Path, version: str) -> None:
    path.write_text(f"{version}\n")


VERSION_PATTERNS = {
    "pyproject.toml": re.compile(r'^(version\s*=\s*")[^"]*(")', re.M),
    "package.json": re.compile(r'^(\s*"version":\s*")[^"]*(")', re.M),
    "Cargo.toml": re.compile(r'^(version\s*=\s*")[^"]*(")', re.M),
    "composer.json": re.compile(r'^(\s*"version":\s*")[^"]*(")', re.M),
    "manifest.json": re.compile(r'^(\s*"version":\s*")[^"]*(")', re.M),
    "pom.xml": re.compile(r"^(  <version>)[^<]*(</version>)", re.M),
}
INIT_RE = re.compile(r'^(__version__\s*=\s*")[^"]*(")', re.M)

CONSTANT_PATTERNS = {
    "**/*.go": re.compile(r'^(const Version\s*=\s*")[^"]*(")', re.M),
    "src/lib.rs": re.compile(r'^(pub const VERSION: &str\s*=\s*")[^"]*(")', re.M),
    "src/index.ts": re.compile(r'^(export const VERSION\s*=\s*")[^"]*(")', re.M),
    "src/Version.php": re.compile(r"^(\s*public const VERSION\s*=\s*')[^']*(')", re.M),
    "src/main/java/**/Version.java": re.compile(
        r'^(\s*public static final String VERSION\s*=\s*")[^"]*(")', re.M
    ),
}


def sync_files(root: Path, version: str) -> list[str]:
    """Write `version` into every manifest, `__version__` and version constant found. Returns the files touched."""
    touched = []

    for name, pattern in VERSION_PATTERNS.items():
        path = root / name

        if not path.exists():
            continue

        text = path.read_text()
        updated = pattern.sub(rf"\g<1>{version}\g<2>", text)

        if updated != text:
            path.write_text(updated)
            touched.append(name)

    for init in sorted(root.glob("*/__init__.py")):
        text = init.read_text()
        updated = INIT_RE.sub(rf"\g<1>{version}\g<2>", text)

        if updated != text:
            init.write_text(updated)
            touched.append(str(init.relative_to(root)))

    for glob, pattern in CONSTANT_PATTERNS.items():
        for path in sorted(root.glob(glob)):
            if path.is_dir() or "node_modules" in path.parts or "vendor" in path.parts:
                continue

            text = path.read_text()
            updated = pattern.sub(rf"\g<1>{version}\g<2>", text)

            if updated != text:
                path.write_text(updated)
                touched.append(str(path.relative_to(root)))

    return touched
