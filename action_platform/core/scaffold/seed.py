"""The version a repository joining the platform starts from, and where it was read."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from action_platform.core.files import CHANGELOG_FILE, LAST_VERSION_FILE
from action_platform.core.flow.repository import Repository
from action_platform.core.release.components import Component
from action_platform.core.release.versioning import SEMVER_RE, VersionFiles

HEADING = re.compile(
    r"^##\s+\[?v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)\]?(?=\s|$)", re.MULTILINE
)
OWN_HEADING = re.compile(r"^## v\d+\.\d+\.\d+\S* — ")
ANY_HEADING = re.compile(r"^## .*$", re.MULTILINE)


@dataclass(frozen=True)
class Seed:
    file: str
    version: str
    source: str

    def __str__(self) -> str:
        return f"{self.file} {self.version} from {self.source}"


def seed(
    repo: Repository,
    component: Component | None = None,
    version: str | None = None,
) -> tuple[Seed, list[str]]:
    """LAST_VERSION of `component` (the root when None): `version` when given; else the higher of its newest release tag and the version its manifest declares, warning when they disagree; else the newest CHANGELOG heading; else 0.0.0."""
    component = component or Component()
    where = component.dir(Path(repo.path))
    file = (
        LAST_VERSION_FILE
        if component.root
        else f"{component.path.rstrip('/')}/{LAST_VERSION_FILE}"
    )

    if version:
        if not SEMVER_RE.match(version.removeprefix("v")):
            raise ValueError(f"not a version: {version!r} (X.Y.Z)")

        return Seed(file, version.removeprefix("v"), "--version"), []

    tag = newest_tag(repo.tags(), component)
    declared = declared_version(where)
    warnings: list[str] = []

    if tag and declared and _key(declared[0]) != _key(tag[0]):
        higher = max((tag, declared), key=lambda found: _key(found[0]))
        warnings.append(
            f"{declared[1]} declares {declared[0]} and the newest release is {tag[1]}; "
            f"{file} starts at the higher, {higher[0]}"
        )

        return Seed(file, higher[0], higher[1]), warnings

    found = tag or declared or changelog_version(where / CHANGELOG_FILE)

    if found:
        return Seed(file, found[0], found[1]), warnings

    return Seed(
        file, "0.0.0", "no release tag, manifest version or CHANGELOG entry"
    ), warnings


def newest_tag(tags: list[str], component: Component) -> tuple[str, str] | None:
    """The highest release among `<name>/vX.Y.Z` tags of a component, or `vX.Y.Z` and `X.Y.Z` of the root; a pre-release only while no stable release follows it."""
    prefix = "" if component.root else f"{component.name}/"
    found = [
        (m.group(0), t)
        for t in tags
        if t.startswith(prefix)
        and (m := SEMVER_RE.match(t[len(prefix) :].removeprefix("v")))
    ]

    if not found:
        return None

    version, tag = max(found, key=lambda f: _key(f[0]))

    return version, f"tag {tag}"


def declared_version(root: Path) -> tuple[str, str] | None:
    """The version the first manifest under `root` declares — the files `release` rewrites."""
    found = VersionFiles(root).declared()

    if found is None or not SEMVER_RE.match(found[0]):
        return None

    return found


def changelog_version(path: Path) -> tuple[str, str] | None:
    if not path.is_file():
        return None

    found = HEADING.search(path.read_text(errors="replace"))

    return (found.group(1), path.name) if found else None


def changelog_style(path: Path) -> str | None:
    """The first release heading of an existing CHANGELOG when `release` writes its entries in another format; None when it matches or there is none."""
    if not path.is_file():
        return None

    first = ANY_HEADING.search(path.read_text(errors="replace"))

    if first is None or OWN_HEADING.match(first.group(0)):
        return None

    return first.group(0).strip()


def _key(version: str) -> tuple:
    found = SEMVER_RE.match(version)

    if found is None:
        return ()

    major, minor, patch, pre = found.groups()
    identifiers = tuple(
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in (pre or "").split(".")
    )

    return int(major), int(minor), int(patch), pre is None, identifiers
