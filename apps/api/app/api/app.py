import hmac
import os
import logging
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from action_platform.core.exception import ActionPlatformError, ConfigError
from app.core.errors import ServiceError
from action_platform.observability import observe
from action_platform.plugins import registry
from action_platform.settings import settings
from app import api_version
from app.api.gate import AccessGate
from app.api.routes import router as routes
from app.services.integrations.plugins import DbOptions
from app.core.auth.crypto import Sealer
from app.services.auth.errors import AuthError
from app.core.auth.secrets import Secrets
from app.core.db import Database
from app.core.shared.urls import GitUrl
from app.repositories.workspace.source import configure_registry, get_registry

log = logging.getLogger("action_platform.api")

OPEN_PATHS = {
    "/api/version",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/.well-known/openid-configuration",
    "/.well-known/jwks.json",
}
SELF_AUTHENTICATED = ("/api/v1/", "/api/auth/")


def build(
    cors_origins: Optional[list[str]] = None,
    token: Optional[str] = None,
    database_url: Optional[str] = None,
    auth_secret: Optional[str] = None,
    public_url: Optional[str] = None,
) -> FastAPI:
    observe("api", version=api_version())
    app = FastAPI(title="action-platform", version=api_version())
    get_registry.cache_clear()
    app.state.db = None
    url = settings.database.url if database_url is None else database_url

    if not url:
        raise ConfigError(
            "AP_DATABASE_URL is empty: the API keeps accounts, apps and jobs in a database."
        )

    app.state.db = Database(
        url, settings.database.pool_size, settings.database.max_overflow
    )

    if settings.database.auto_migrate:
        app.state.db.migrate()
    elif app.state.db.behind():
        log.warning(
            "database behind head: run `action-platform-api db migrate` — /api/version reports ready=false until then"
        )
    configure_registry(app.state.db)
    registry.use_options(lambda slug: DbOptions(app.state.db, slug))

    secret = settings.api.auth_secret if auth_secret is None else auth_secret
    app.state.secrets = Secrets(secret) if secret else None
    app.state.sealer = Sealer(app.state.secrets) if app.state.secrets else None
    base = (settings.api.public_url if public_url is None else public_url).rstrip("/")
    app.state.verification_uri = f"{base}/device"
    app.state.public_url = base
    expected = settings.api.token if token is None else token

    if not expected and not settings.api.allow_unauthenticated:
        raise ConfigError(
            "AP_API_TOKEN is empty: every route would be open. Set the shared secret "
            "(the web app sends it as Authorization: Bearer) or, for local development "
            "only, AP_ALLOW_UNAUTHENTICATED=1."
        )

    if expected:

        @app.middleware("http")
        async def _require_token(request: Request, call_next):
            if (
                request.url.path in OPEN_PATHS
                or request.url.path.startswith(SELF_AUTHENTICATED)
                or request.method == "OPTIONS"
                or getattr(request.state, "caller", None) is not None
            ):
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
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "authorization",
                "content-type",
                "x-organization",
                "x-session-token",
                "x-session-cookie",
                "x-action-platform-client",
            ],
        )

    @app.exception_handler(AuthError)
    def _auth_error(_, exc: AuthError):
        return JSONResponse(
            status_code=exc.status,
            content={
                "detail": exc.detail,
                "error": exc.code,
                "error_description": exc.detail,
            },
        )

    @app.exception_handler(ServiceError)
    def _service_error(_, exc: ServiceError):
        detail = {"code": exc.code, "detail": str(exc)} if exc.code else str(exc)

        return JSONResponse(status_code=exc.status, content={"detail": detail})

    @app.exception_handler(ActionPlatformError)
    def _platform_error(_, exc: ActionPlatformError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(routes)

    def repo_of(registry_id: str) -> Optional[str]:
        try:
            return GitUrl(get_registry().get(registry_id).url).repo
        except ActionPlatformError:
            return None

    app.add_middleware(AccessGate, state=app.state, repo_of=repo_of)

    return app


def create_app() -> FastAPI:
    origins = [o for o in os.environ.get("AP_CORS", "").split(",") if o]

    return build(origins or None)


def serve(
    host: str,
    port: int,
    cors_origins: Optional[list[str]] = None,
    reload: bool = False,
    workers: int = 1,
) -> None:
    """One uvicorn process by default; `workers` > 1 forks that many, each with its own pool — the clone cache is per process, so a request may fetch what another process already has."""
    if reload:
        os.environ["AP_CORS"] = ",".join(cors_origins or [])
        uvicorn.run(
            "app.api.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            reload_dirs=[str(Path(__file__).resolve().parents[1])],
            log_level="info",
        )
        return

    if workers > 1:
        os.environ["AP_CORS"] = ",".join(cors_origins or [])
        uvicorn.run(
            "app.api.app:create_app",
            factory=True,
            host=host,
            port=port,
            workers=workers,
            log_level="warning",
            proxy_headers=True,
            forwarded_allow_ips=settings.api.forwarded_allow_ips,
        )
        return

    uvicorn.run(
        build(cors_origins),
        host=host,
        port=port,
        log_level="warning",
        proxy_headers=True,
        forwarded_allow_ips=settings.api.forwarded_allow_ips,
    )
