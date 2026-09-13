import hmac
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from action_platform import __version__
from action_platform.api.core.deps import get_registry
from action_platform.api.v1 import router as v1
from action_platform.core.exception import ActionPlatformError
from action_platform.observability import observe
from action_platform.settings import settings

OPEN_PATHS = {"/api/version", "/docs", "/openapi.json", "/redoc"}


def build(
    cors_origins: Optional[list[str]] = None, token: Optional[str] = None
) -> FastAPI:
    observe("api")
    app = FastAPI(title="action-platform", version=__version__)
    get_registry.cache_clear()
    expected = settings.API_TOKEN if token is None else token

    if expected:

        @app.middleware("http")
        async def _require_token(request: Request, call_next):
            if request.url.path in OPEN_PATHS or request.method == "OPTIONS":
                return await call_next(request)

            header = request.headers.get("authorization", "")
            given = header[7:] if header.lower().startswith("bearer ") else ""

            if not hmac.compare_digest(given, expected):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "missing or invalid API token"},
                )

            return await call_next(request)

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
