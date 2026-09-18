"""`/api/v1/*`: the ASGI gate — reads the body, asks the planner (off the event loop) who calls and what the call becomes, rewrites the scope for `/api/*`, and queues the code-host import after a successful call."""

import json
from typing import Any, Callable, Optional

from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from action_platform.core.exception import ActionPlatformError
from app.core.errors import Refused, ServiceError
from app.schemas.common import SourceCredentials
from app.services.access.planner import Plan, Planner, Queued
from app.services.workspace.git_auth import git_auth

PREFIX = "/api/v1/"
MAX_BODY = 2 * 1024 * 1024


class AccessGate:
    def __init__(
        self, app: ASGIApp, state: Any, repo_of: Callable[[str], Optional[str]]
    ) -> None:
        self.app = app
        self.state = state
        self.repo_of = repo_of
        self.planner = Planner(state)

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
                self.planner.decide, headers, method, path, body
            )
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

        scope.setdefault("state", {})["caller"] = caller

        if plan is None:
            await self.app(scope, self._replay(body), send)

            return

        self._rewrite(scope, path, plan)
        creds = SourceCredentials(**plan.credentials) if plan.credentials else None

        with git_auth(creds):
            status = await self._pass(scope, plan.body, send)

        if plan.target.rule.imports and 200 <= status < 300:
            await run_in_threadpool(
                self.planner.import_later, plan, caller, path, method
            )

    @staticmethod
    def _rewrite(scope: Scope, path: str, plan: Plan) -> None:
        scope["path"] = "/api/" + path
        scope["raw_path"] = scope["path"].encode()
        scope["method"] = plan.method
        scope["headers"] = [
            (k, v)
            for k, v in scope["headers"]
            if k not in (b"content-length", b"content-type")
        ] + [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(plan.body)).encode()),
        ]

        if plan.allowed_registry_ids is not None:
            scope["state"]["allowed_registry_ids"] = plan.allowed_registry_ids

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
