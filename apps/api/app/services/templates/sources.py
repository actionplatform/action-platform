"""Which template repository a request reads from, and the matrix as the API presents it."""

from typing import Optional

from action_platform.core.scaffold.templates import (
    Matrix,
    TemplateSource,
    load_matrix,
    load_source,
)
from action_platform.settings import settings
from app.services.workspace import git_auth as auth
from app.schemas import SourceSpec

OFFICIAL_REF = settings.TEMPLATES_REF


class TemplateRepos:
    """Which checkout and matrix a request should use: a custom source, or the official repository."""

    @staticmethod
    def source(spec: SourceSpec) -> TemplateSource:
        return TemplateSource(url=spec.url, ref=spec.ref, name=spec.name)

    @classmethod
    def resolve(cls, spec: SourceSpec | None):
        if spec is None:
            return load_matrix()

        with auth.git_auth(spec.credentials):
            return load_source(cls.source(spec))


class MatrixView:
    """One templates matrix as the API answers it: every path absolute, every entry tagged with its source."""

    def __init__(
        self, m: Matrix, source: str, base: str, repo_url: str = "", ref: str = ""
    ) -> None:
        self.m = m
        self.source = source
        self.base = base
        self.tree = (
            f"{repo_url.rstrip('/').removesuffix('.git')}/tree/{ref}"
            if repo_url
            else ""
        )

    @staticmethod
    def raw_base(url: str, ref: str) -> str:
        """Where a repository's files are served raw, for icons: GitHub and GitLab are known, anything else has no icons."""
        clean = url.rstrip("/").removesuffix(".git")

        if "github.com/" in clean:
            return f"https://raw.githubusercontent.com/{clean.split('github.com/', 1)[1]}/{ref}"

        if "gitlab" in clean:
            return f"{clean}/-/raw/{ref}"

        return ""

    def absolute(self, path: str) -> Optional[str]:
        if not path:
            return None

        if path.startswith(("http://", "https://")):
            return path

        return f"{self.base}/{path.lstrip('/')}" if self.base else None

    def url(self, directory: str) -> Optional[str]:
        return f"{self.tree}/{directory}" if self.tree and directory else None

    def as_dict(self) -> dict:
        stack_icons = {info.id: info.icon for info in self.m.stack_infos}

        return {
            "projects": [
                {
                    "type": leaf.type,
                    "stack": leaf.stack,
                    "template": leaf.template,
                    "default": leaf.default,
                    "description": leaf.description,
                    "source": self.source,
                    "plain": leaf.plain,
                    "framework": leaf.framework or None,
                    "language": leaf.language or leaf.stack or None,
                    "icon": self.absolute(leaf.icon),
                    "stack_icon": self.absolute(stack_icons.get(leaf.stack, "")),
                    "path": leaf.directory or None,
                    "url": self.url(leaf.directory),
                }
                for leaf in self.m.leaves
            ],
            "clouds": [
                {
                    "name": c.name,
                    "types": c.types,
                    "languages": c.languages,
                    "description": c.description,
                    "source": self.source,
                    "icon": self.absolute(c.icon),
                    "url": self.url(c.directory) if self.tree else None,
                }
                for c in self.m.clouds
            ],
            "services": [
                {
                    "name": s.name,
                    "providers": s.providers,
                    "description": s.description,
                    "source": self.source,
                    "icon": self.absolute(s.icon),
                    "url": self.url(s.directory) if self.tree else None,
                }
                for s in self.m.services
            ],
            "types": [
                {"id": t.id, "label": t.label, "description": t.description}
                for t in self.m.type_infos
            ],
            "stacks": [
                {"id": t.id, "label": t.label, "icon": self.absolute(t.icon)}
                for t in self.m.stack_infos
            ],
        }
