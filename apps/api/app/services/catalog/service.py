from typing import Optional

from action_platform import __version__
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow import gitflow
from action_platform.plugins import registry
from action_platform.core.scaffold.templates import (
    OFFICIAL,
    Matrix,
    TemplateSource,
    load_matrix,
    load_source,
)
from action_platform.settings import settings
from app import api_version
from app.core.shared import git_auth as auth
from app.schemas import SourceSpec
from app.services.catalog.published import index
from app.services.catalog.published import plugins_index as published_plugins

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


class CatalogService:
    def version(self) -> dict:
        return {"version": __version__, "api": api_version()}

    def matrix(self, sources: list[SourceSpec] | None = None) -> dict:
        published = index.get() if settings.TEMPLATES_DIR is None else None

        if published:
            official = Matrix.from_dict(published)
            base = index.raw_base
        else:
            _, official = load_matrix()
            base = MatrixView.raw_base(settings.TEMPLATES_REPO, OFFICIAL_REF)

        out = MatrixView(
            official, OFFICIAL, base, settings.TEMPLATES_REPO, OFFICIAL_REF
        ).as_dict()
        out["sources"] = [
            {
                "name": OFFICIAL,
                "url": settings.TEMPLATES_REPO,
                "ref": OFFICIAL_REF,
                "ok": True,
                "projects": len(official.leaves),
                "clouds": len(official.clouds),
                "services": len(official.services),
            }
        ]

        for spec in sources or []:
            status = {"name": spec.name, "url": spec.url, "ref": spec.ref, "ok": True}

            try:
                _, m = TemplateRepos.resolve(spec)
            except (ActionPlatformError, OSError) as e:
                status.update(ok=False, error=str(e))
                out["sources"].append(status)
                continue

            extra = MatrixView(
                m,
                spec.name,
                MatrixView.raw_base(spec.url, spec.ref),
                spec.url,
                spec.ref,
            ).as_dict()

            for key in ("projects", "clouds", "services"):
                out[key].extend(extra[key])

            for key in ("types", "stacks"):
                known = {row["id"] for row in out[key]}
                out[key].extend(row for row in extra[key] if row["id"] not in known)

            status.update(
                projects=len(m.leaves), clouds=len(m.clouds), services=len(m.services)
            )
            out["sources"].append(status)

        return out

    def plugins(self) -> dict:
        """The marketplace: what the plugins index publishes, and which of them this platform runs."""
        published = published_plugins.get() or {}
        plugins = registry.installed()
        installed = {row["slug"]: row for row in plugins.rows()}
        remembered = plugins.state.plugins
        pending = set(plugins.state.restart_pending())
        rows = []

        for row in published.get("plugins") or []:
            slug = row.get("name") or ""
            here = installed.get(slug)
            kept = remembered.get(slug)
            error = registry.FAILURES.get(slug) if here is None and kept else None
            rows.append(
                {
                    "slug": slug,
                    "description": row.get("description") or "",
                    "author": row.get("author") or "",
                    "verified": bool(row.get("verified")),
                    "repo": row.get("repo") or "",
                    "pypi": row.get("pypi") or "",
                    "latest": row.get("latest") or "",
                    "min_core": row.get("min_core") or "",
                    "needs": list(row.get("needs") or []),
                    "tags": list(row.get("tags") or []),
                    "installed": here is not None or kept is not None,
                    "installed_version": here["version"]
                    if here
                    else (kept.version if kept else None),
                    "enabled": bool(here and here["enabled"]),
                    "restart_pending": slug in pending,
                    "error": error,
                }
            )

        return {
            "plugins": rows,
            "index": settings.PLUGINS_INDEX_URL,
            "hosted": settings.PLUGINS_DIR is not None,
            "restart_pending": sorted(pending),
        }

    def gitflow_rules(self) -> dict:
        return {
            "kinds": sorted(gitflow.current().kinds),
            "protected": sorted(gitflow.current().protected),
            "types": sorted(gitflow.current().types),
        }
