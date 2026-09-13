"""Template matrix: fetch the templates repo, resolve project leaves, cloud overlays and services."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.core.flow.git import UnsafeUrl, check_remote_url, git_env
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


@dataclass(frozen=True)
class TemplateSource:
    """A git repository laid out like actionplatform/templates: index.toml plus projects/, cloud/, service/."""

    url: str
    ref: str = "v1"
    name: str = ""

    @classmethod
    def parse(cls, spec: str, name: str = "") -> "TemplateSource":
        """`url[@ref]`; a local path is accepted as well."""
        url, _, ref = spec.rpartition("@")

        if not url or "/" in ref or ref.startswith("git"):
            url, ref = spec, "v1"

        return cls(url=url, ref=ref or "v1", name=name)

    @property
    def label(self) -> str:
        return self.name or self.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")

    @property
    def cache(self) -> Path:
        key = hashlib.sha256(f"{self.url}@{self.ref}".encode()).hexdigest()[:16]

        return settings.TEMPLATES_CACHE.parent / "sources" / key


def ensure_source(source: TemplateSource, update: bool = False) -> Path:
    """Return a local checkout of `source` at its ref, cloning or fetching as needed."""
    cache = source.cache

    try:
        check_remote_url(source.url)
    except UnsafeUrl as e:
        raise TemplateError(str(e)) from e

    if not cache.exists():
        logger.info("cloning %s@%s", source.url, source.ref)
        cache.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", "--branch", source.ref, source.url, str(cache))
        return cache

    try:
        _git("-C", str(cache), "fetch", "--depth", "1", "--quiet", "origin", source.ref)
        _git("-C", str(cache), "checkout", "--quiet", "--force", "FETCH_HEAD")
    except TemplateError as e:
        if update:
            raise
        logger.warning(
            "source %s not refreshed (%s); using local copy", source.label, e
        )

    return cache


LANGUAGE_MARKERS = [
    ("pyproject.toml", "python"),
    ("go.mod", "go"),
    ("package.json", "node"),
    ("composer.json", "php"),
    ("pom.xml", "java"),
    ("Cargo.toml", "rust"),
    ("requirements.txt", "python"),
    ("setup.py", "python"),
    ("Pipfile", "python"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "java"),
    ("tsconfig.json", "node"),
]

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".go": "go",
    ".ts": "node",
    ".tsx": "node",
    ".js": "node",
    ".jsx": "node",
    ".php": "php",
    ".java": "java",
    ".kt": "java",
    ".rs": "rust",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
    "target",
}


def detect_language(root: Path) -> str:
    """Language of a repository: by manifest file first, then by the most common source extension."""
    for marker, language in LANGUAGE_MARKERS:
        if (root / marker).exists():
            return language

    counts: dict[str, int] = {}

    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        language = LANGUAGE_EXTENSIONS.get(path.suffix)

        if language and path.is_file():
            counts[language] = counts.get(language, 0) + 1

    return max(counts, key=counts.get) if counts else ""


def plain_matrix(source: TemplateSource, repo: Path) -> Matrix:
    """A repository without index.toml is one template: its own tree, copied as-is."""
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
    repo = ensure_source(source, update=update)
    index = repo / "index.toml"

    if not index.exists():
        return repo, plain_matrix(source, repo)

    return repo, Matrix.from_toml(index)


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


def load_matrix(update: bool = False, source: str | None = None) -> tuple[Path, Matrix]:
    if source:
        return load_source(TemplateSource.parse(source), update=update)

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
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, env=git_env()
    )

    if result.returncode != 0:
        raise TemplateError(result.stderr.strip() or "git failed")
