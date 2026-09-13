from action_platform import __version__
from action_platform.api import api_version
from action_platform.api.core import credentials as auth
from action_platform.api.schemas import SourceSpec
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


def as_source(spec: SourceSpec) -> TemplateSource:
    return TemplateSource(url=spec.url, ref=spec.ref, name=spec.name)


def resolve_repo(spec: SourceSpec | None):
    """The checkout and matrix a request should use: a custom source, or the official repository."""
    if spec is None:
        return load_matrix()

    with auth.git_auth(spec.credentials):
        return load_source(as_source(spec))


def _serialize(m: Matrix, source: str) -> dict:
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
            }
            for c in m.clouds
        ],
        "services": [
            {
                "name": s.name,
                "providers": s.providers,
                "description": s.description,
                "source": source,
            }
            for s in m.services
        ],
    }


class CatalogService:
    def version(self) -> dict:
        return {"version": __version__, "api": api_version()}

    def matrix(self, sources: list[SourceSpec] | None = None) -> dict:
        _, official = load_matrix()
        out = _serialize(official, OFFICIAL)
        out["sources"] = [
            {
                "name": OFFICIAL,
                "url": settings.TEMPLATES_REPO,
                "ref": "v1",
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

            extra = _serialize(m, spec.name)

            for key in ("projects", "clouds", "services"):
                out[key].extend(extra[key])

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
