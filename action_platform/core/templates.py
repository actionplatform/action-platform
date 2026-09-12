"""Template matrix: fetch the templates repo, resolve project leaves, cloud overlays and services."""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.logging import logger
from action_platform.settings import settings


@dataclass
class Leaf:
    """A project template: type/stack/template under `projects/`."""

    type: str
    stack: str
    template: str
    description: str = ""
    default: bool = False

    @property
    def directory(self) -> str:
        if not self.stack:
            return f"projects/{self.type}"

        return f"projects/{self.type}/{self.stack}/{self.template}"


@dataclass
class Cloud:
    """A deploy overlay under `cloud/`, applied on top of a generated project."""

    name: str
    description: str = ""
    languages: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)

    @property
    def directory(self) -> str:
        return f"cloud/{self.name}"

    def supports(self, type_: str, language: str) -> bool:
        type_ok = not self.types or type_ in self.types
        language_ok = not self.languages or language in self.languages

        return type_ok and language_ok


@dataclass
class Service:
    """An application dependency under `service/`, added to a project as `services/<name>/`."""

    name: str
    description: str = ""
    providers: list[str] = field(default_factory=list)

    @property
    def directory(self) -> str:
        return f"service/{self.name}"


def _is_leaf_table(table: dict) -> bool:
    return not any(isinstance(v, dict) for v in table.values())


def _walk(table: dict, path: tuple[str, ...] = ()):
    """Yield (path, meta) for every leaf table, however deep."""
    if not table:
        return

    if _is_leaf_table(table):
        yield path, table
        return

    for key, value in table.items():
        if isinstance(value, dict):
            yield from _walk(value, (*path, key))


@dataclass
class Matrix:
    leaves: list[Leaf] = field(default_factory=list)
    clouds: list[Cloud] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: Path) -> "Matrix":
        if not path.exists():
            raise TemplateError(f"index.toml not found at {path}")

        data = tomllib.loads(path.read_text())

        leaves = []
        for keys, meta in _walk(data.get("projects", {})):
            type_, stack, template = (*keys, "", "")[:3]
            leaves.append(
                Leaf(
                    type_,
                    stack,
                    template,
                    meta.get("description", ""),
                    bool(meta.get("default", False)),
                )
            )

        clouds = [
            Cloud(
                "/".join(keys),
                meta.get("description", ""),
                list(meta.get("languages", [])),
                list(meta.get("types", [])),
            )
            for keys, meta in _walk(data.get("cloud", {}))
        ]

        services = [
            Service(
                "/".join(keys),
                meta.get("description", ""),
                list(meta.get("providers", [])),
            )
            for keys, meta in _walk(data.get("service", {}))
        ]

        return cls(leaves, clouds, services)

    def types(self) -> list[str]:
        return sorted({leaf.type for leaf in self.leaves})

    def stacks(self, type_: str) -> list[str]:
        return sorted(
            {leaf.stack for leaf in self.leaves if leaf.type == type_ and leaf.stack}
        )

    def templates(self, type_: str, stack: str) -> list[Leaf]:
        return [
            leaf for leaf in self.leaves if leaf.type == type_ and leaf.stack == stack
        ]

    def resolve(self, type_: str, stack: str | None, template: str | None) -> Leaf:
        if type_ not in self.types():
            raise TemplateError(
                f"unknown type: {type_} (available: {', '.join(self.types())})"
            )

        stacks = self.stacks(type_)

        if not stacks:
            return next(leaf for leaf in self.leaves if leaf.type == type_)

        if stack is None:
            raise TemplateError(
                f"type {type_} requires a stack (available: {', '.join(stacks)})"
            )

        if stack not in stacks:
            raise TemplateError(
                f"unknown stack: {type_}/{stack} (available: {', '.join(stacks)})"
            )

        candidates = self.templates(type_, stack)

        if template is None:
            defaults = [leaf for leaf in candidates if leaf.default]

            if not defaults:
                raise TemplateError(f"no default template for {type_}/{stack}")

            return defaults[0]

        for leaf in candidates:
            if leaf.template == template:
                return leaf

        names = ", ".join(leaf.template for leaf in candidates)

        raise TemplateError(
            f"unknown template: {type_}/{stack}/{template} (available: {names})"
        )

    def cloud(self, name: str) -> Cloud:
        for cloud in self.clouds:
            if cloud.name == name:
                return cloud

        names = ", ".join(c.name for c in self.clouds)

        raise TemplateError(f"unknown cloud: {name} (available: {names})")

    def clouds_for(self, type_: str, language: str) -> list[Cloud]:
        return [c for c in self.clouds if c.supports(type_, language)]

    def service(self, name: str) -> Service:
        for service in self.services:
            if service.name == name:
                return service

        names = ", ".join(s.name for s in self.services)

        raise TemplateError(f"unknown service: {name} (available: {names})")


def ensure_repo(update: bool = False) -> Path:
    """Return a local checkout of the templates repo, cloning or pulling as needed."""
    local = settings.TEMPLATES_DIR

    if local is not None:
        path = Path(local).expanduser()

        if not path.exists():
            raise TemplateError(
                f"ACTION_PLATFORM_TEMPLATES points to missing path: {path}"
            )

        return path

    cache = settings.TEMPLATES_CACHE

    if not cache.exists():
        logger.info("cloning %s", settings.TEMPLATES_REPO)
        cache.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", settings.TEMPLATES_REPO, str(cache))
        return cache

    try:
        _git("-C", str(cache), "pull", "--ff-only", "--quiet")
    except TemplateError as e:
        if update:
            raise
        logger.warning("templates cache not refreshed (%s); using local copy", e)

    return cache


def load_matrix(update: bool = False) -> tuple[Path, Matrix]:
    repo = ensure_repo(update=update)
    matrix = Matrix.from_toml(repo / "index.toml")

    if not matrix.leaves and not update and settings.TEMPLATES_DIR is None:
        logger.info("templates cache has no projects, refreshing")
        repo = ensure_repo(update=True)
        matrix = Matrix.from_toml(repo / "index.toml")

    if not matrix.leaves:
        raise TemplateError(
            f"no projects in {repo / 'index.toml'} — run with --update "
            "or check ACTION_PLATFORM_TEMPLATES"
        )

    return repo, matrix


def _git(*args: str) -> None:
    result = subprocess.run(["git", *args], capture_output=True, text=True)

    if result.returncode != 0:
        raise TemplateError(result.stderr.strip() or "git failed")
