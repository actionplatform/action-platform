"""The template matrix: project leaves, cloud overlays and services, read from index.json or from a plain repository."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.detect import detect_language
from action_platform.core.scaffold.store import LocalTemplateStore, TemplateSource
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
    plain: bool = False
    framework: str = ""
    icon: str = ""
    language: str = ""

    @property
    def directory(self) -> str:
        if self.plain:
            return ""

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
    icon: str = ""

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
    icon: str = ""

    @property
    def directory(self) -> str:
        return f"service/{self.name}"


@dataclass
class TypeInfo:
    """What a project type is called and means, from `[types.<id>]`."""

    id: str
    label: str = ""
    description: str = ""


@dataclass
class StackInfo:
    """What a stack is called and its icon, from `[stacks.<id>]`."""

    id: str
    label: str = ""
    icon: str = ""


@dataclass
class Matrix:
    leaves: list[Leaf] = field(default_factory=list)
    clouds: list[Cloud] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    type_infos: list[TypeInfo] = field(default_factory=list)
    stack_infos: list[StackInfo] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Path) -> "Matrix":
        if not path.exists():
            raise TemplateError(f"index.json not found at {path}")

        try:
            data = json.loads(path.read_text())
        except ValueError as e:
            raise TemplateError(f"{path} is not valid JSON: {e}") from e

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "Matrix":
        """The shape of `index.json`: `types`, `stacks`, `projects`, `clouds`, `services`, each a list of objects with an `id`."""
        leaves = []

        for row in data.get("projects", []):
            parts = (row.get("id") or "").split("/")
            type_ = row.get("type") or (parts[0] if parts else "")
            stack = row.get("stack") or (parts[1] if len(parts) > 1 else "")
            template = row.get("template") or (parts[2] if len(parts) > 2 else "")
            icons = row.get("icons") or {}
            leaves.append(
                Leaf(
                    type_,
                    stack or "",
                    template or "",
                    row.get("description", ""),
                    bool(row.get("default", False)),
                    framework=row.get("framework") or "",
                    icon=icons.get("framework") or row.get("icon") or "",
                    language=row.get("language") or "",
                )
            )

        clouds = [
            Cloud(
                row["id"],
                row.get("description", ""),
                list(row.get("languages", [])),
                list(row.get("types", [])),
                row.get("icon") or "",
            )
            for row in data.get("clouds", [])
        ]

        services = [
            Service(
                row["id"],
                row.get("description", ""),
                list(row.get("providers", [])),
                row.get("icon") or "",
            )
            for row in data.get("services", [])
        ]

        type_infos = [
            TypeInfo(row["id"], row.get("label", row["id"]), row.get("description", ""))
            for row in data.get("types", [])
        ]
        stack_infos = [
            StackInfo(row["id"], row.get("label", row["id"]), row.get("icon") or "")
            for row in data.get("stacks", [])
        ]

        return cls(leaves, clouds, services, type_infos, stack_infos)

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
        if template is not None:
            for leaf in self.leaves:
                if leaf.plain and leaf.template == template:
                    return replace(leaf, type=type_ or leaf.type)

        if type_ not in self.types():
            raise TemplateError(
                f"unknown type: {type_} (available: {', '.join(self.types())})"
            )

        if template is not None:
            for leaf in self.leaves:
                if (
                    leaf.type == type_
                    and leaf.template == template
                    and (stack is None or leaf.stack == stack or not leaf.stack)
                ):
                    return leaf

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


OFFICIAL = "official"


def plain_matrix(source: TemplateSource, repo: Path) -> Matrix:
    """A repository without index.json is one template: its own tree, copied as-is."""
    meta: dict = {}
    manifest = repo / settings.CONFIG_FILE

    if manifest.exists():
        try:
            meta = tomllib.loads(manifest.read_text()).get("project", {})
        except tomllib.TOMLDecodeError:
            meta = {}

    language = meta.get("language") or detect_language(repo)
    type_ = meta.get("type") or (
        "library"
        if language
        and not (repo / "Dockerfile").exists()
        and not (repo / "app").is_dir()
        else "web"
    )

    leaf = Leaf(
        type=type_,
        stack=language,
        template=source.label,
        description=meta.get("description")
        or f"Repository {source.url}@{source.ref}, copied as-is",
        default=True,
        plain=True,
    )

    return Matrix(leaves=[leaf])


def load_source(source: TemplateSource, update: bool = False) -> tuple[Path, Matrix]:
    repo = LocalTemplateStore().checkout(source, update=update)
    index = repo / "index.json"

    if not index.exists():
        return repo, plain_matrix(source, repo)

    return repo, Matrix.from_json(index)


def ensure_repo(update: bool = False) -> Path:
    return LocalTemplateStore().official(update=update)


def ensure_source(source: TemplateSource, update: bool = False) -> Path:
    return LocalTemplateStore().checkout(source, update=update)


def load_matrix(update: bool = False, source: str | None = None) -> tuple[Path, Matrix]:
    if source:
        return load_source(TemplateSource.parse(source), update=update)

    repo = ensure_repo(update=update)
    matrix = Matrix.from_json(repo / "index.json")

    if not matrix.leaves and not update and settings.TEMPLATES_DIR is None:
        logger.info("templates cache has no projects, refreshing")
        repo = ensure_repo(update=True)
        matrix = Matrix.from_json(repo / "index.json")

    if not matrix.leaves:
        raise TemplateError(
            f"no projects in {repo / 'index.json'} — run with --update "
            "or check ACTION_PLATFORM_TEMPLATES"
        )

    return repo, matrix
