"""Template matrix: fetch the templates repo and resolve type/stack/template."""

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
    type: str
    stack: str
    template: str
    description: str = ""
    default: bool = False

    @property
    def directory(self) -> str:
        if not self.stack:
            return self.type
        return f"{self.type}/{self.stack}/{self.template}"


@dataclass
class Matrix:
    leaves: list[Leaf] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: Path) -> "Matrix":
        if not path.exists():
            raise TemplateError(f"index.toml not found at {path}")
        data = tomllib.loads(path.read_text())
        leaves: list[Leaf] = []
        for type_, stacks in data.items():
            if "description" in stacks and not any(
                isinstance(v, dict) for v in stacks.values()
            ):
                leaves.append(Leaf(type_, "", "", stacks.get("description", "")))
                continue
            for stack, templates in stacks.items():
                for template, meta in templates.items():
                    leaves.append(
                        Leaf(
                            type_,
                            stack,
                            template,
                            meta.get("description", ""),
                            bool(meta.get("default", False)),
                        )
                    )
        return cls(leaves)

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
    elif update:
        logger.info("updating templates")
        _git("-C", str(cache), "pull", "--ff-only", "--quiet")
    return cache


def load_matrix(update: bool = False) -> tuple[Path, Matrix]:
    repo = ensure_repo(update=update)
    return repo, Matrix.from_toml(repo / "index.toml")


def _git(*args: str) -> None:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise TemplateError(result.stderr.strip() or "git failed")
