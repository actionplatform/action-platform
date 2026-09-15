"""Calls that leave the request: an async sync/release/deploy/push becomes a job, and the code-host import after a call always does."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.core.db.models import App, Organization
from app.services.access.caller import Caller
from app.services.jobs import JobQueue

ASYNC_PATH = re.compile(r"^apps/([^/]+)/(sync|release|deploy|push)$")


def wants_async(headers: dict[str, str]) -> bool:
    return (
        "respond-async" in headers.get("prefer", "").lower()
        or headers.get("x-async") == "1"
    )


class Dispatcher:
    def __init__(self, queue: JobQueue) -> None:
        self.queue = queue

    def _payload(
        self,
        organization: Organization,
        app: App,
        caller: Caller,
        path: str,
        method: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "path": path,
            "method": method,
            "body": body,
            "registry_id": app.registry_id,
            "organization_id": organization.id,
            "app_id": app.id,
            "user_id": caller.user.id,
        }

    def async_job(
        self,
        organization: Optional[Organization],
        app: Optional[App],
        caller: Caller,
        path: str,
        method: str,
        headers: dict[str, str],
        body: Optional[dict[str, Any]],
    ) -> Optional[str]:
        """The job id when the caller asked for the call to run on the worker; None when it runs inline."""
        queued = ASYNC_PATH.match(path)

        if not (
            body is not None
            and queued
            and app is not None
            and organization is not None
            and wants_async(headers)
        ):
            return None

        kind = queued.group(2)
        job = self.queue.enqueue(
            kind,
            self._payload(
                organization,
                app,
                caller,
                path,
                method,
                {k: v for k, v in body.items() if k != "credentials"},
            ),
            organization_id=organization.id,
            app_id=app.id,
            dedupe_key=kind if kind == "sync" else None,
        )

        return job.id

    def import_later(
        self,
        organization: Organization,
        app: App,
        caller: Caller,
        path: str,
        method: str,
    ) -> None:
        """Releases and pull requests are copied from the code host by the worker after the answer went out — never on the request's clock."""
        self.queue.enqueue(
            "import",
            self._payload(organization, app, caller, path, method, {}),
            organization_id=organization.id,
            app_id=app.id,
            dedupe_key="import",
        )
