"""Release components: parts of one repository that version independently.

    [components.web]
    path = "apps/web"

    [components.api]
    path = "action_platform/api"

The root component is the repository itself. Each component keeps its own
LAST_VERSION and CHANGELOG.md under `path`, is tagged `<name>/vX.Y.Z`
(root: `vX.Y.Z`) and its changelog only lists commits that touched
`path`; the root's changelog excludes every component's path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.exception import ReleaseError


@dataclass(frozen=True)
class Component:
    name: str = ""
    path: str = "."
    excludes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def root(self) -> bool:
        return not self.name

    @property
    def tag_prefix(self) -> str:
        return f"{self.name}/v" if self.name else "v"

    def tag(self, version: str) -> str:
        return f"{self.tag_prefix}{version}"

    @property
    def tag_glob(self) -> str:
        return f"{self.tag_prefix}*"

    def dir(self, repo_root: Path) -> Path:
        return repo_root / self.path if self.path != "." else repo_root

    def pathspecs(self) -> list[str]:
        if self.root:
            return ["."] + [f":!{p}" for p in self.excludes]

        return [self.path]

    def label(self, version: str) -> str:
        return f"{self.name} {version}" if self.name else version


def parse(spec: dict) -> dict[str, Component]:
    """`[components]` table of platform.toml → name → Component, plus the root under ""."""
    named = {
        name: Component(name=name, path=str(body.get("path", name)))
        for name, body in spec.items()
        if isinstance(body, dict)
    }
    root = Component(excludes=tuple(c.path for c in named.values()))

    return {"": root, **named}


def resolve(components: dict[str, Component], name: str | None) -> Component:
    if not name:
        return components[""]

    try:
        return components[name]
    except KeyError:
        known = ", ".join(sorted(k for k in components if k)) or "none"

        raise ReleaseError(f"unknown component: {name} (available: {known})") from None
