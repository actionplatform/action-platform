from fastapi import APIRouter

from action_platform.api import schemas
from action_platform.api.services.catalog import CatalogService

router = APIRouter(tags=["catalog"])
service = CatalogService()


@router.get("/version")
def version() -> schemas.Version:
    return service.version()


@router.get("/matrix")
def matrix() -> schemas.Matrix:
    return service.matrix()


@router.get("/gitflow/rules")
def gitflow_rules() -> schemas.GitflowRules:
    return service.gitflow_rules()
