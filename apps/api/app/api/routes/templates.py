from fastapi import APIRouter, Request

from app.schemas import catalog as schemas
from app.services.integrations.plugins.catalog import PluginsCatalog
from app.services.templates import CatalogService

router = APIRouter(prefix="/api", tags=["catalog"])
service = CatalogService()


@router.get("/version")
def version(request: Request) -> schemas.Version:
    """Versions, and readiness: `ready` is false while the database waits for a migration."""
    db = getattr(request.app.state, "db", None)
    behind = db.behind() if db is not None else False

    return schemas.Version(
        **service.version(),
        ready=not behind,
        database="behind" if behind else ("up to date" if db is not None else None),
    )


@router.get("/matrix")
def matrix() -> schemas.Matrix:
    return service.matrix()


@router.post("/matrix")
def matrix_with_sources(
    body: schemas.SourcesRequest,
) -> schemas.Matrix:
    return service.matrix(body.sources)


@router.get("/plugins")
def plugins() -> schemas.Plugins:
    return PluginsCatalog().rows()


@router.get("/gitflow/rules")
def gitflow_rules() -> schemas.GitflowRules:
    return service.gitflow_rules()
