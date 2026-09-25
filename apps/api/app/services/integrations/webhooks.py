"""Deliveries from the code host: verified against the host's secret, matched to the app by repository, turned into a sync job."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from app.core.auth.crypto import Sealer
from app.core.db.models import App
from app.core.errors import Forbidden, NotFound
from app.core.shared.urls import GitUrl
from app.repositories.projects import ProjectsRepository
from app.repositories.workspace.registry import Registry
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.jobs import JobQueue

GITHUB_EVENTS = {"push", "pull_request", "release", "workflow_run", "create", "delete"}
GITLAB_EVENTS = {
    "Push Hook",
    "Tag Push Hook",
    "Merge Request Hook",
    "Release Hook",
    "Pipeline Hook",
}
BITBUCKET_EVENTS = {
    "repo:push",
    "pullrequest:created",
    "pullrequest:updated",
    "pullrequest:fulfilled",
    "pullrequest:rejected",
}


@dataclass
class Delivery:
    kind: str
    event: str
    repo: Optional[str]
    accepted: bool


class Webhooks:
    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer],
        registry: Registry,
        queue: JobQueue,
    ) -> None:
        self.db = db
        self.directory = IntegrationsDirectory(db, sealer)
        self.projects = ProjectsRepository(db, sealer)
        self.registry = registry
        self.queue = queue

    def receive(
        self, host_id: str, headers: dict[str, str], body: bytes
    ) -> dict[str, Any]:
        host = self.directory.host_by_id(host_id)

        if host is None or not host.webhook_secret_encrypted:
            raise NotFound("no webhook for this host")

        secret = self.directory.webhook_secret(host.organization_id, host.id)
        self._verify(host.kind, secret or "", headers, body)
        delivery = self._parse(host.kind, headers, body)

        if not delivery.accepted or not delivery.repo:
            return {"event": delivery.event, "repo": delivery.repo, "queued": []}

        queued = []

        for app in self._apps_for(host.organization_id, delivery.repo):
            job = self.queue.enqueue(
                "sync",
                {
                    "path": f"apps/{app.registry_id}/sync",
                    "method": "POST",
                    "body": {},
                    "registry_id": app.registry_id,
                    "organization_id": host.organization_id,
                    "app_id": app.id,
                    "user_id": None,
                    "webhook": {"kind": host.kind, "event": delivery.event},
                },
                organization_id=host.organization_id,
                app_id=app.id,
                dedupe_key="sync",
            )
            queued.append(job.id)

        return {"event": delivery.event, "repo": delivery.repo, "queued": queued}

    @staticmethod
    def _verify(kind: str, secret: str, headers: dict[str, str], body: bytes) -> None:
        if not secret:
            raise Forbidden("this host has no webhook secret; set one in Settings")

        if kind == "github":
            given = headers.get("x-hub-signature-256", "")
            expected = (
                "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            )
        elif kind == "gitlab":
            given = headers.get("x-gitlab-token", "")
            expected = secret
        elif kind == "bitbucket":
            given = headers.get("x-hub-signature", "")
            expected = (
                "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            )
        else:
            raise Forbidden("this host kind does not deliver webhooks")

        if not given or not hmac.compare_digest(given, expected):
            raise Forbidden("webhook signature does not match")

    @staticmethod
    def _parse(kind: str, headers: dict[str, str], body: bytes) -> Delivery:
        try:
            payload = json.loads(body or b"{}")
        except ValueError:
            payload = {}

        if kind == "github":
            event = headers.get("x-github-event", "")
            repo = (payload.get("repository") or {}).get("full_name")

            return Delivery(kind, event, repo, event in GITHUB_EVENTS)

        if kind == "gitlab":
            event = headers.get("x-gitlab-event", "")
            repo = (payload.get("project") or {}).get("path_with_namespace")

            return Delivery(kind, event, repo, event in GITLAB_EVENTS)

        event = headers.get("x-event-key", "")
        repo = (payload.get("repository") or {}).get("full_name")

        return Delivery(kind, event, repo, event in BITBUCKET_EVENTS)

    def _apps_for(self, organization_id: str, repo: str) -> list[App]:
        wanted = repo.lower().removesuffix(".git")
        matches = []

        for entry in self.registry.list():
            found = GitUrl(entry.url).repo if entry.url else None

            if found and found.lower() == wanted:
                pair = self.projects.app_by_registry_id(entry.id)

                if pair and pair[1].organization_id == organization_id:
                    matches.append(pair[0])

        return matches


__all__ = ["Delivery", "Webhooks"]
