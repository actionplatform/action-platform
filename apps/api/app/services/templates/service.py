"""The templates catalog the API answers: the version, the matrix (official plus the organization's sources), the git-flow rules."""

from action_platform import __version__
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow import gitflow
from action_platform.core.scaffold.catalog import (
    OFFICIAL,
    Matrix,
    load_matrix,
    with_plugin_clouds,
)
from action_platform.settings import settings
from app import api_version
from app.schemas import SourceSpec
from app.services.templates.published import index
from app.services.templates.sources import MatrixView, TemplateRepos


class CatalogService:
    def version(self) -> dict:
        return {"version": __version__, "api": api_version()}

    def matrix(self, sources: list[SourceSpec] | None = None) -> dict:
        published = index.get() if settings.templates.dir is None else None

        if published:
            official = with_plugin_clouds(Matrix.from_dict(published))
            base = index.raw_base
        else:
            _, official = load_matrix()
            base = MatrixView.raw_base(settings.templates.repo, settings.templates.ref)

        out = MatrixView(
            official, OFFICIAL, base, settings.templates.repo, settings.templates.ref
        ).as_dict()
        out["sources"] = [
            {
                "name": OFFICIAL,
                "url": settings.templates.repo,
                "ref": settings.templates.ref,
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

    def gitflow_rules(self) -> dict:
        return {
            "kinds": sorted(gitflow.current().kinds),
            "protected": sorted(gitflow.current().protected),
            "types": sorted(gitflow.current().types),
        }
