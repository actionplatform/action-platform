import json
import re
from typing import Any, Callable, Optional

from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from action_platform.core.exception import ActionPlatformError
from app.core.errors import ServiceError
from app.core.access.rules import (
    DIRECTORY,
    WORKSPACE_ROOTS,
    rule_for,
)
from app.core.auth.service import AuthService
from app.core.db.models import App, Organization, Project
from app.services.access.caller import Caller, resolve_caller
from app.services.access.enrich import enrich
from app.services.directory import DirectoryService
from app.services.jobs import JobQueue

PREFIX = "/api/v1/"
MAX_BODY = 2 * 1024 * 1024

ASYNC_PATH = re.compile(r"^apps/([^/]+)/(sync|release|deploy|push)$")


class Queued(Exception):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


def wants_async(headers: dict[str, str]) -> bool:
    return (
        "respond-async" in headers.get("prefer", "").lower()
        or headers.get("x-async") == "1"
    )


class Refused(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail


class AccessGate:
    """`/api/v1/*`: identifies the caller, applies role ∩ scope ∩ reach, fills in credentials and template sources, then hands the call to `/api/*`."""

    def __init__(
        self, app: ASGIApp, state: Any, repo_of: Callable[[str], Optional[str]]
    ) -> None:
        self.app = app
        self.state = state
        self.repo_of = repo_of

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(PREFIX):
            await self.app(scope, receive, send)

            return

        if self.state.db is None or self.state.secrets is None:
            await self._json(
                send,
                503,
                {"detail": "no database or auth secret configured on the API"},
            )

            return

        try:
            body = await self._read(receive)
        except Refused as e:
            await self._json(send, e.status, {"detail": e.detail})

            return

        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        path = scope["path"][len(PREFIX) :].strip("/")
        method = scope["method"]

        try:
            caller, plan = await run_in_threadpool(
                self._decide, headers, method, path, body
            )
        except Refused as e:
            await self._json(send, e.status, {"detail": e.detail})

            return
        except Queued as e:
            await self._json(
                send,
                202,
                {
                    "job": e.job_id,
                    "status": "queued",
                    "poll": f"/api/v1/jobs/{e.job_id}",
                },
            )

            return
        except ServiceError as e:
            detail = {"code": e.code, "detail": str(e)} if e.code else str(e)
            await self._json(send, e.status, {"detail": detail})

            return
        except ActionPlatformError as e:
            await self._json(send, 400, {"detail": str(e)})

            return

        if plan is None:
            scope.setdefault("state", {})["caller"] = caller
            await self.app(scope, self._replay(body), send)

            return

        rule, organization, app, new_body, new_method = plan
        scope["path"] = "/api/" + path
        scope["raw_path"] = scope["path"].encode()
        scope["method"] = new_method
        scope["headers"] = [
            (k, v)
            for k, v in scope["headers"]
            if k not in (b"content-length", b"content-type")
        ] + [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(new_body)).encode()),
        ]
        scope.setdefault("state", {})["caller"] = caller

        if method == "GET" and path == "apps":
            scope["state"]["allowed_registry_ids"] = await run_in_threadpool(
                self._reach, caller, organization
            )

        status = await self._pass(scope, new_body, send)

        if (
            rule.imports
            and app is not None
            and organization is not None
            and 200 <= status < 300
        ):
            await run_in_threadpool(
                self._import_later, organization, app, caller, path, method
            )

    def _decide(
        self, headers: dict[str, str], method: str, path: str, body: bytes
    ) -> tuple[Caller, Optional[tuple]]:
        """Who calls and what the call becomes — the database work of the gate, run off the event loop."""
        with self.state.db.session() as db:
            auth = AuthService(db, self.state.secrets, self.state.verification_uri)
            caller = resolve_caller(headers, db, auth)

            if caller is None:
                raise Refused(401, "unauthorized")

            if caller.organization is None and not caller.all_organizations:
                raise Refused(403, "no organization")

            if path in DIRECTORY or path.split("/")[0] not in WORKSPACE_ROOTS:
                return caller, None

            return caller, self._plan(db, caller, method, path, headers, body)

    def _reach(self, caller: Caller, organization: Optional[Organization]) -> set[str]:
        allowed: set[str] = set()

        with self.state.db.session() as db:
            directory = DirectoryService(db)

            for org in (
                [organization] if organization else [o for o, _ in caller.organizations]
            ):
                allowed |= directory.registry_ids_of(
                    org.id, caller.project_id, caller.app_id
                )

        return allowed

    def _plan(
        self,
        db,
        caller: Caller,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
    ):
        rule = rule_for(method, path)

        if rule is None:
            raise Refused(404, f"{method} /api/v1/{path} is not exposed")

        directory = DirectoryService(db, self.state.sealer)
        segments = path.split("/")
        registry_id = (
            segments[1]
            if path.startswith("apps/") and len(segments) > 1 and segments[1] != "init"
            else None
        )
        app: Optional[App] = None
        project: Optional[Project] = None
        organization: Optional[Organization] = None

        if registry_id:
            found = directory.app_by_registry_id(registry_id)

            if found:
                app, project = found
                organization = caller.member_of(project.organization_id)

            if (
                app is None
                or organization is None
                or (caller.organization and caller.organization.id != organization.id)
            ):
                raise Refused(404, "app not found")
        else:
            organization = self._requested(caller, headers) or (
                None if method == "GET" and path == "apps" else caller.organization
            )

            if organization is None and not (method == "GET" and path == "apps"):
                raise Refused(
                    400,
                    "this token spans every organization: send X-Organization: <id or slug>",
                )

        ok, why = caller.allows(
            organization.id if organization else None, rule.permission
        )

        if not ok:
            raise Refused(403, why)

        if (
            app is not None
            and project is not None
            and not caller.within_reach(app.id, project.id)
        ):
            raise Refused(404, "app not found")

        if (
            app is None
            and method == "POST"
            and path in ("apps", "apps/init")
            and (caller.project_id or caller.app_id)
        ):
            raise Refused(
                403, "this token is limited to one project; it cannot add apps"
            )

        new_method = method
        parsed: Optional[dict] = None

        if method not in ("GET", "HEAD"):
            try:
                parsed = json.loads(body) if body else {}
            except ValueError as e:
                raise Refused(400, "body is not valid JSON") from e

            if not isinstance(parsed, dict):
                raise Refused(400, "body must be a JSON object")

        if method == "GET" and path == "matrix" and organization is not None:
            new_method = "POST"
            parsed = {"sources": directory.source_specs_of(organization.id)}

        queued = ASYNC_PATH.match(path)

        if (
            parsed is not None
            and queued
            and app is not None
            and organization is not None
            and wants_async(headers)
        ):
            job = JobQueue(self.state.db).enqueue(
                queued.group(2),
                {
                    "path": path,
                    "method": method,
                    "body": {k: v for k, v in parsed.items() if k != "credentials"},
                    "registry_id": app.registry_id,
                    "organization_id": organization.id,
                    "app_id": app.id,
                    "user_id": caller.user.id,
                },
                organization_id=organization.id,
                app_id=app.id,
                dedupe_key=queued.group(2) if queued.group(2) == "sync" else None,
            )

            raise Queued(job.id)

        if parsed is not None:
            parsed = enrich(directory, organization, app, path, parsed, rule)

        if rule.imports and app is not None:
            directory.mark_synced(app)

        new_body = json.dumps(parsed).encode() if parsed is not None else b""

        return rule, organization, app, new_body, new_method

    @staticmethod
    @staticmethod
    def _requested(caller: Caller, headers: dict[str, str]) -> Optional[Organization]:
        wanted = (headers.get("x-organization") or "").strip()

        if wanted and (caller.all_organizations or caller.scope is None):
            found = caller.member_of(wanted)

            if found is not None:
                return found

        return caller.organization

    def _import_later(
        self,
        organization: Organization,
        app: App,
        caller: Caller,
        path: str,
        method: str,
    ) -> None:
        """Releases and pull requests are copied from the code host by the worker, after the answer went out — never on the request's clock."""
        JobQueue(self.state.db).enqueue(
            "import",
            {
                "path": path,
                "method": method,
                "body": {},
                "registry_id": app.registry_id,
                "organization_id": organization.id,
                "app_id": app.id,
                "user_id": caller.user.id,
            },
            organization_id=organization.id,
            app_id=app.id,
            dedupe_key="import",
        )

    @staticmethod
    async def _read(receive: Receive) -> bytes:
        """The body, up to `MAX_BODY` — every call the gate accepts is a small JSON document."""
        chunks = []
        size = 0

        while True:
            message = await receive()
            chunk = message.get("body", b"")
            size += len(chunk)

            if size > MAX_BODY:
                raise Refused(
                    413, f"request body larger than {MAX_BODY // (1024 * 1024)} MB"
                )

            chunks.append(chunk)

            if not message.get("more_body"):
                break

        return b"".join(chunks)

    @staticmethod
    def _replay(body: bytes) -> Receive:
        sent = False

        async def receive() -> Message:
            nonlocal sent

            if sent:
                return {"type": "http.disconnect"}

            sent = True

            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    async def _pass(self, scope: Scope, body: bytes, send: Send) -> int:
        status = 500

        async def sender(message: Message) -> None:
            nonlocal status

            if message["type"] == "http.response.start":
                status = message["status"]

            await send(message)

        await self.app(scope, self._replay(body), sender)

        return status

    @staticmethod
    async def _json(send: Send, status: int, payload: Any) -> None:
        data = json.dumps(payload).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(data)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": data, "more_body": False})
