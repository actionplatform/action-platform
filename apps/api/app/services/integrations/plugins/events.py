"""The organization's events, handed to the bundled plugins that take them: one queued delivery per plugin and destination, retried by the job queue with backoff, and read back by the organization's admins."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session as DbSession

from action_platform.core.events import Event
from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry
from action_platform.settings import settings
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Job, Organization, Project
from app.core.shared.clock import now
from app.services.integrations.plugins.options import DbOptions, ReadOptions, opened
from app.services.jobs.queue import CHANNEL, loads

KIND = "plugin_event"
RECENT = timedelta(days=1)

log = logging.getLogger(__name__)


class PluginEvents:
    """Raises the organization's events from inside the session that records what happened, so a delivery is queued exactly when the change is committed."""

    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer],
        public_url: Optional[str] = None,
    ) -> None:
        self.db = db
        self.sealer = sealer
        self.public_url = (
            settings.api.public_url if public_url is None else public_url
        ).rstrip("/")

    def emit(
        self,
        app: Optional[App],
        kind: str,
        payload: dict[str, Any],
        actor: Optional[str] = None,
        page: str = "",
        at: Optional[datetime] = None,
    ) -> int:
        """Queue `kind` for every listening plugin whose options route it; an event older than a day (a history import) is not news and goes nowhere. Never raises: what happened stays recorded whatever a plugin does."""
        if at is not None and at.tzinfo is not None:
            at = at.astimezone(timezone.utc).replace(tzinfo=None)

        if app is None or (at is not None and at < now() - RECENT):
            return 0

        try:
            return self._emit(app, kind, payload, actor, page)
        except Exception:
            log.warning("event %s of app %s not queued", kind, app.id, exc_info=True)

            return 0

    def _emit(
        self,
        app: App,
        kind: str,
        payload: dict[str, Any],
        actor: Optional[str],
        page: str,
    ) -> int:
        listeners = registry.installed().listeners()

        if not listeners:
            return 0

        project = self.db.get(Project, app.project_id)
        organization = (
            self.db.get(Organization, project.organization_id) if project else None
        )

        if project is None or organization is None:
            return 0

        event = Event(
            kind,
            organization.slug,
            project.slug,
            app.name,
            actor,
            payload,
            url=self._url(project, app, page),
            id=str(uuid.uuid4()),
            at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        queued = 0

        for row in listeners:
            try:
                options = opened(self.db, row.slug, organization.id, self.sealer)
                routes = row.plugin.routes(event, ReadOptions(row.slug, options))
            except Exception as e:
                log.warning("plugin %s.routes failed: %s", row.slug, e)

                continue

            for route in dict.fromkeys(routes):
                self.db.add(
                    Job(
                        id=str(uuid.uuid4()),
                        kind=KIND,
                        status="queued",
                        organization_id=organization.id,
                        payload=json.dumps(
                            {
                                "organization_id": organization.id,
                                "app_id": app.id,
                                "plugin": row.slug,
                                "route": route,
                                "event": event.as_dict(),
                            }
                        ),
                        run_after=now(),
                    )
                )
                queued += 1

        if queued:
            self.db.flush()
            self._wake()

        return queued

    def _url(self, project: Project, app: App, page: str) -> Optional[str]:
        if not self.public_url:
            return None

        base = f"{self.public_url}/projects/{project.id}/apps/{app.id}"

        return f"{base}/{page}" if page else base

    def _wake(self) -> None:
        bind = self.db.get_bind()

        if bind.dialect.name != "postgresql":
            return

        try:
            self.db.execute(text(f"NOTIFY {CHANNEL}"))
        except Exception:
            log.debug("NOTIFY %s failed", CHANNEL, exc_info=True)


def deliver(
    database: Database, sealer: Optional[Sealer], payload: dict[str, Any]
) -> dict[str, Any]:
    """One queued delivery: the plugin sends the event to its route with the organization's options, secrets opened. A plugin removed or switched off since is a refusal, not a retry."""
    slug = str(payload.get("plugin") or "")
    plugins = registry.installed()
    row = plugins.get(slug)

    if not plugins.is_enabled(slug):
        raise ActionPlatformError(f"plugin {slug} is disabled")

    event = Event.from_dict(payload.get("event") or {})
    route = str(payload.get("route") or "")
    row.plugin.deliver(
        event,
        route,
        DbOptions(database, slug, str(payload.get("organization_id") or ""), sealer),
    )

    return {"plugin": slug, "route": route, "event": event.kind}


def deliveries(
    database: Database, slug: str, organization_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """The organization's latest deliveries of the plugin, newest first."""
    rows: list[dict[str, Any]] = []

    with database.session() as s:
        jobs = s.scalars(
            select(Job)
            .where(
                Job.kind == KIND,
                Job.organization_id == organization_id,
                Job.payload.contains(f'"plugin": {json.dumps(slug)}'),
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )

        for job in jobs:
            payload = loads(job.payload)

            if payload.get("plugin") != slug:
                continue

            event = (
                payload.get("event") if isinstance(payload.get("event"), dict) else {}
            )
            rows.append(
                {
                    "id": job.id,
                    "event": str(event.get("kind") or ""),
                    "route": str(payload.get("route") or ""),
                    "project": str(event.get("project") or ""),
                    "app": str(event.get("app") or ""),
                    "url": event.get("url"),
                    "status": job.status,
                    "attempts": job.attempts,
                    "error": job.error,
                    "created_at": job.created_at,
                    "finished_at": job.finished_at,
                }
            )

    return rows
