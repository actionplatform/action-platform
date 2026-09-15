from fastapi import APIRouter

from app import schemas
from app.services.catalog import CatalogService

router = APIRouter(prefix="/api", tags=["catalog"])
service = CatalogService()


@router.get("/version")
def version() -> schemas.Version:
    return service.version()


@router.get("/matrix")
def matrix() -> schemas.Matrix:
    return service.matrix()


@router.post("/matrix")
def matrix_with_sources(body: schemas.SourcesRequest) -> schemas.Matrix:
    return service.matrix(body.sources)


@router.get("/gitflow/rules")
def gitflow_rules() -> schemas.GitflowRules:
    return service.gitflow_rules()
