from typing import Optional

from action_platform import __version__
from action_platform.api import api_version
from action_platform.api.core import credentials as auth
from action_platform.api.schemas import SourceSpec
from action_platform.api.services.index import index
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow import gitflow
from action_platform.core.scaffold.templates import (
    OFFICIAL,
    Matrix,
    TemplateSource,
    load_matrix,
    load_source,
)
from action_platform.settings import settings

OFFICIAL_REF = settings.TEMPLATES_REF


def as_source(spec: SourceSpec) -> TemplateSource:
    return TemplateSource(url=spec.url, ref=spec.ref, name=spec.name)


def resolve_repo(spec: SourceSpec | None):
    """The checkout and matrix a request should use: a custom source, or the official repository."""
    if spec is None:
        return load_matrix()

    with auth.git_auth(spec.credentials):
        return load_source(as_source(spec))


def raw_base(url: str, ref: str) -> str:
    """Where a repository's files are served raw, for icons: GitHub and GitLab are known, anything else has no icons."""
    clean = url.rstrip("/").removesuffix(".git")

    if "github.com/" in clean:
        return f"https://raw.githubusercontent.com/{clean.split('github.com/', 1)[1]}/{ref}"

    if "gitlab" in clean:
        return f"{clean}/-/raw/{ref}"

    return ""


def _absolute(base: str, path: str) -> Optional[str]:
    if not path:
        return None

    if path.startswith(("http://", "https://")):
        return path

    return f"{base}/{path.lstrip('/')}" if base else None


def _serialize(
    m: Matrix, source: str, base: str, repo_url: str = "", ref: str = ""
) -> dict:
    stack_icons = {info.id: info.icon for info in m.stack_infos}
    tree = f"{repo_url.rstrip('/').removesuffix('.git')}/tree/{ref}" if repo_url else ""

    return {
        "projects": [
            {
                "type": leaf.type,
                "stack": leaf.stack,
                "template": leaf.template,
                "default": leaf.default,
                "description": leaf.description,
                "source": source,
                "plain": leaf.plain,
                "framework": leaf.framework or None,
                "language": leaf.language or leaf.stack or None,
                "icon": _absolute(base, leaf.icon),
                "stack_icon": _absolute(base, stack_icons.get(leaf.stack, "")),
                "path": leaf.directory or None,
                "url": f"{tree}/{leaf.directory}" if tree and leaf.directory else None,
            }
            for leaf in m.leaves
        ],
        "clouds": [
            {
                "name": c.name,
                "types": c.types,
                "languages": c.languages,
                "description": c.description,
                "source": source,
                "icon": _absolute(base, c.icon),
                "url": f"{tree}/{c.directory}" if tree else None,
            }
            for c in m.clouds
        ],
        "services": [
            {
                "name": s.name,
                "providers": s.providers,
                "description": s.description,
                "source": source,
                "icon": _absolute(base, s.icon),
                "url": f"{tree}/{s.directory}" if tree else None,
            }
            for s in m.services
        ],
        "types": [
            {"id": t.id, "label": t.label, "description": t.description}
            for t in m.type_infos
        ],
        "stacks": [
            {"id": t.id, "label": t.label, "icon": _absolute(base, t.icon)}
            for t in m.stack_infos
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
            base = raw_base(settings.TEMPLATES_REPO, OFFICIAL_REF)

        out = _serialize(
            official, OFFICIAL, base, settings.TEMPLATES_REPO, OFFICIAL_REF
        )
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
                _, m = resolve_repo(spec)
            except (ActionPlatformError, OSError) as e:
                status.update(ok=False, error=str(e))
                out["sources"].append(status)
                continue

            extra = _serialize(
                m, spec.name, raw_base(spec.url, spec.ref), spec.url, spec.ref
            )

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

    def gitflow_rules(self) -> dict:
        return {
            "kinds": sorted(gitflow.KINDS),
            "protected": sorted(gitflow.PROTECTED),
            "types": sorted(gitflow.TYPES),
        }
