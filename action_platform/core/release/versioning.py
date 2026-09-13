"""Semantic versions as values, and the files a project keeps its version in."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from action_platform.core.exception import ActionPlatformError

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([\w.]+))?$")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    pre: str | None = None

    @classmethod
    def parse(cls, text: str) -> "Version":
        match = SEMVER_RE.match(text.strip().lstrip("v"))

        if not match:
            raise ActionPlatformError(f"Invalid semver: {text!r}")

        major, minor, patch, pre = match.groups()

        return cls(int(major), int(minor), int(patch), pre)

    @classmethod
    def is_valid(cls, text: str) -> bool:
        return bool(SEMVER_RE.match(text.strip().lstrip("v")))

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"

        return f"{base}-{self.pre}" if self.pre else base

    @property
    def stable(self) -> "Version":
        return Version(self.major, self.minor, self.patch)

    @property
    def is_prerelease(self) -> bool:
        return self.pre is not None

    def bump(self, level: str) -> "Version":
        """`major` / `minor` / `patch`, or an explicit version to jump to."""
        if level == "major":
            return Version(self.major + 1, 0, 0)

        if level == "minor":
            return Version(self.major, self.minor + 1, 0)

        if level == "patch":
            return Version(self.major, self.minor, self.patch + 1)

        return Version.parse(level)

    def next_rc(self, existing_tags: list[str]) -> "Version":
        """This stable version plus the next -rc.N not yet tagged."""
        prefix = f"v{self.stable}-rc."
        taken = [
            int(t[len(prefix) :])
            for t in existing_tags
            if t.startswith(prefix) and t[len(prefix) :].isdigit()
        ]

        return Version(
            self.major, self.minor, self.patch, f"rc.{max(taken, default=0) + 1}"
        )


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


class VersionFiles:
    """LAST_VERSION plus every manifest, `__version__` and version constant under one directory."""

    def __init__(self, root: Path, last_version_file: str = "LAST_VERSION") -> None:
        self.root = Path(root)
        self.last = self.root / last_version_file

    def read(self) -> str:
        return self.last.read_text().strip() if self.last.exists() else "0.0.0"

    def write(self, version: str) -> None:
        self.last.write_text(f"{version}\n")

    def sync(self, version: str) -> list[str]:
        """Write `version` everywhere it is declared. Returns the files touched, relative to the root."""
        touched = []

        for name, pattern in VERSION_PATTERNS.items():
            if self._rewrite(self.root / name, pattern, version):
                touched.append(name)

        for init in sorted(self.root.glob("*/__init__.py")):
            if self._rewrite(init, INIT_RE, version):
                touched.append(str(init.relative_to(self.root)))

        for glob, pattern in CONSTANT_PATTERNS.items():
            for path in sorted(self.root.glob(glob)):
                if (
                    path.is_dir()
                    or "node_modules" in path.parts
                    or "vendor" in path.parts
                ):
                    continue

                if self._rewrite(path, pattern, version):
                    touched.append(str(path.relative_to(self.root)))

        return touched

    @staticmethod
    def _rewrite(path: Path, pattern: re.Pattern, version: str) -> bool:
        if not path.exists():
            return False

        text = path.read_text()
        updated = pattern.sub(rf"\g<1>{version}\g<2>", text)

        if updated == text:
            return False

        path.write_text(updated)

        return True


def parse(version: str) -> tuple[int, int, int, str | None]:
    v = Version.parse(version)

    return v.major, v.minor, v.patch, v.pre


def bump(version: str, level: str) -> str:
    return str(Version.parse(version).bump(level))


def strip_pre(version: str) -> str:
    return str(Version.parse(version).stable)


def next_rc(base: str, existing_tags: list[str]) -> str:
    return str(Version.parse(base).next_rc(existing_tags))


def read(path: Path) -> str:
    return VersionFiles(path.parent, path.name).read()


def write(path: Path, version: str) -> None:
    VersionFiles(path.parent, path.name).write(version)


def sync_files(root: Path, version: str) -> list[str]:
    return VersionFiles(root).sync(version)
