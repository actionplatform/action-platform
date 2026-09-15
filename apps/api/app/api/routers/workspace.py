from fastapi import APIRouter

from app.api.routers import actions, apps, catalog, configuration, flow

router = APIRouter(prefix="/api")
router.include_router(catalog.router)
router.include_router(apps.router)
router.include_router(actions.router)
router.include_router(flow.router)
router.include_router(configuration.router)
