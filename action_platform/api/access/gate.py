import json
import re
from typing import Any, Callable, Optional

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from action_platform.api.access.caller import Caller, resolve_caller
from action_platform.api.access.rules import DIRECTORY, rule_for
from action_platform.api.auth.service import AuthService
from action_platform.api.db.models import App, Organization, Project
from action_platform.api.services.directory import DirectoryService
from action_platform.api.services.imports import ImportService
from action_platform.core.exception import ActionPlatformError

PREFIX = "/api/v1/"
REPO_IN_URL = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$")
SOURCE_BODY = re.compile(r"^apps/(init|[^/]+/(cloud|services))$")


def repo_from_url(url: str) -> Optional[str]:
    match = REPO_IN_URL.search(url or "")
    return match.group(1) if match else None


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

        body = await self._read(receive)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        path = scope["path"][len(PREFIX) :].strip("/")
        method = scope["method"]

        try:
            with self.state.db.session() as db:
                auth = AuthService(db, self.state.secrets, self.state.verification_uri)
                caller = resolve_caller(headers, db, auth)
                if caller is None:
                    raise Refused(401, "unauthorized")
                if caller.organization is None and not caller.all_organizations:
                    raise Refused(403, "no organization")
                if path in DIRECTORY:
                    scope.setdefault("state", {})["caller"] = caller
                    plan = None
                else:
                    plan = self._plan(db, caller, method, path, headers, body)
        except Refused as e:
            await self._json(send, e.status, {"detail": e.detail})
            return
        except ActionPlatformError as e:
            await self._json(send, 400, {"detail": str(e)})
            return

        if plan is None:
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
            allowed: set[str] = set()
            with self.state.db.session() as db:
                directory = DirectoryService(db)
                for org in (
                    [organization]
                    if organization
                    else [o for o, _ in caller.organizations]
                ):
                    allowed |= directory.registry_ids_of(
                        org.id, caller.project_id, caller.app_id
                    )
            await self._filtered(scope, new_body, send, allowed)
            return

        status = await self._pass(scope, new_body, send)
        if (
            rule.imports
            and app is not None
            and organization is not None
            and 200 <= status < 300
        ):
            self._import(organization, app)

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

        if (
            parsed is not None
            and organization is not None
            and SOURCE_BODY.match(path)
            and isinstance(parsed.get("source"), str)
        ):
            parsed["source"] = directory.source_spec_by_name(
                organization.id, parsed["source"]
            )

        if (
            parsed is not None
            and organization is not None
            and rule.credentials
            and not parsed.get("credentials")
        ):
            host_id = (
                app.source_host_id
                if app
                else directory.host_id_for_url(organization.id, parsed["url"])
                if isinstance(parsed.get("url"), str)
                else None
            )
            creds = directory.credentials_for(organization.id, host_id)
            name, email = directory.git_author_of(organization.id)
            parsed["credentials"] = {
                **(creds.as_dict() if creds else {}),
                "author_name": name,
                "author_email": email,
            }

        if rule.imports and app is not None:
            directory.mark_synced(app)

        new_body = json.dumps(parsed).encode() if parsed is not None else b""
        return rule, organization, app, new_body, new_method

    @staticmethod
    def _requested(caller: Caller, headers: dict[str, str]) -> Optional[Organization]:
        if caller.organization:
            return caller.organization
        wanted = (headers.get("x-organization") or "").strip()
        return caller.member_of(wanted) if wanted else None

    def _import(self, organization: Organization, app: App) -> None:
        repo = self.repo_of(app.registry_id)
        with self.state.db.session() as db:
            directory = DirectoryService(db, self.state.sealer)
            creds = directory.credentials_for(organization.id, app.source_host_id)
            ImportService(db).sync_all(app.id, creds, repo)

    @staticmethod
    async def _read(receive: Receive) -> bytes:
        chunks = []
        while True:
            message = await receive()
            chunks.append(message.get("body", b""))
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

    async def _filtered(
        self, scope: Scope, body: bytes, send: Send, allowed: set[str]
    ) -> None:
        start: Optional[Message] = None
        chunks: list[bytes] = []

        async def collector(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self.app(scope, self._replay(body), collector)
        raw = b"".join(chunks)
        status = start["status"] if start else 500
        try:
            rows = json.loads(raw) if raw else []
        except ValueError:
            rows = []
        if status == 200 and isinstance(rows, list):
            rows = [r for r in rows if isinstance(r, dict) and r.get("id") in allowed]
        await self._json(send, status, rows)

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
