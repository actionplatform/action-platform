"""One /api/v1 call, decided: who calls, what it targets, whether it becomes a job, and the body the inner route receives — every database read of the gate, in one place, off the event loop."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.core.access.rules import DIRECTORY, WORKSPACE_ROOTS
from app.services.auth.service import AuthService
from app.core.errors import Invalid, Refused
from app.repositories.configuration.config_store import ConfigStore
from app.services.scopes import ScopesService
from app.services.access.caller import Caller, resolve_caller
from app.services.access.dispatch import Dispatcher
from app.services.access.enrich import credentials_for, enrich
from app.services.access.target import Authorizer, Target
from app.services.access.directory import AccessDirectory
from app.services.jobs import JobQueue
from app.services.releases import ReadinessRequests

DEPLOY_PATH = re.compile(r"^apps/[^/]+/deploy$")


@dataclass
class Plan:
    target: Target
    body: bytes
    method: str
    allowed_registry_ids: Optional[set[str]] = None
    credentials: Optional[dict[str, Any]] = None


class Queued(Exception):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class Planner:
    def __init__(self, state: Any) -> None:
        self.state = state

    def decide(
        self, headers: dict[str, str], method: str, path: str, body: bytes
    ) -> tuple[Caller, Optional[Plan]]:
        """The caller and, for a workspace route, the plan; None for the directory routes, which check access themselves."""
        with self.state.db.session() as db:
            auth = AuthService(db, self.state.secrets, self.state.verification_uri)
            caller = resolve_caller(headers, db, auth)

            if caller is None:
                raise Refused(401, "unauthorized")

            if caller.organization is None and not caller.all_organizations:
                raise Refused(403, "no organization")

            if path in DIRECTORY or path.split("/")[0] not in WORKSPACE_ROOTS:
                return caller, None

            directory = AccessDirectory(db, self.state.sealer)
            authorizer = Authorizer(directory)
            target = authorizer.target(caller, method, path, headers)
            parsed = self._parse(method, body)
            new_method = method

            if method == "GET" and path == "matrix" and target.organization is not None:
                new_method = "POST"
                parsed = {"sources": directory.source_specs_of(target.organization.id)}

            if (
                method == "POST"
                and DEPLOY_PATH.match(path)
                and target.app is not None
                and parsed is not None
            ):
                parsed["stage"] = parsed.get("scope") or parsed.get("stage") or "dev"
                parsed.pop("scope", None)

                if parsed["stage"] not in self._scope_names(target.app):
                    raise Invalid(
                        f"no scope {parsed['stage']!r}: create it under Deployments › Scopes"
                    )

                ReadinessRequests(
                    self.state.db, JobQueue(self.state.db)
                ).assert_deployable(
                    target.app,
                    parsed.get("version"),
                    parsed["stage"],
                    bool(parsed.get("force")),
                )

            job_id = Dispatcher(JobQueue(self.state.db)).async_job(
                target.organization, target.app, caller, path, method, headers, parsed
            )

            if job_id is not None:
                raise Queued(job_id)

            if parsed is not None:
                parsed = enrich(
                    directory,
                    target.organization,
                    target.app,
                    path,
                    parsed,
                    target.rule,
                )

            credentials = (
                credentials_for(directory, target.organization, target.app, {})
                if target.app is not None and target.organization is not None
                else None
            )

            if target.rule.imports and target.app is not None:
                directory.mark_synced(target.app)

            allowed = (
                authorizer.reach(caller, target.organization)
                if method == "GET" and path == "apps"
                else None
            )
            new_body = json.dumps(parsed).encode() if parsed is not None else b""

            return caller, Plan(target, new_body, new_method, allowed, credentials)

    def _scope_names(self, app: Any) -> list[str]:
        with self.state.db.session() as db:
            return ScopesService(db, ConfigStore(self.state.db)).names(app)

    @staticmethod
    def _parse(method: str, body: bytes) -> Optional[dict]:
        if method in ("GET", "HEAD"):
            return None

        try:
            parsed = json.loads(body) if body else {}
        except ValueError as e:
            raise Refused(400, "body is not valid JSON") from e

        if not isinstance(parsed, dict):
            raise Refused(400, "body must be a JSON object")

        return parsed

    def import_later(self, plan: Plan, caller: Caller, path: str, method: str) -> None:
        if plan.target.app is None or plan.target.organization is None:
            return

        Dispatcher(JobQueue(self.state.db)).import_later(
            plan.target.organization, plan.target.app, caller, path, method
        )
