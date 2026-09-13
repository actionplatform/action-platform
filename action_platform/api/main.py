import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from action_platform import __version__
from action_platform.api.core.deps import get_registry
from action_platform.api.v1 import router as v1
from action_platform.core.exception import ActionPlatformError


def build(cors_origins: Optional[list[str]] = None) -> FastAPI:
    app = FastAPI(title="action-platform", version=__version__)
    get_registry.cache_clear()

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(ActionPlatformError)
    def _platform_error(_, exc: ActionPlatformError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(v1)

    return app


def create_app() -> FastAPI:
    origins = [o for o in os.environ.get("AP_CORS", "").split(",") if o]

    return build(origins or None)


def serve(
    host: str,
    port: int,
    cors_origins: Optional[list[str]] = None,
    reload: bool = False,
) -> None:
    import uvicorn

    if reload:
        os.environ["AP_CORS"] = ",".join(cors_origins or [])
        uvicorn.run(
            "action_platform.api.main:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            reload_dirs=[str(Path(__file__).resolve().parents[1])],
            log_level="info",
        )
        return

    uvicorn.run(build(cors_origins), host=host, port=port, log_level="warning")
