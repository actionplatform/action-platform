"""The periodic sweep: every enforced app gets a `protection` job that reads its host and puts the policy back when it drifted; the sweep schedules the next one."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select

from action_platform.core.exception import ConfigError
from action_platform.core.flow.protection import ProtectionSpec
from app.core.db.database import Database
from app.core.db.models import Job
from app.core.shared.clock import now
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.protection import ProtectionStore

SWEEP_EVERY = timedelta(hours=1)
SWEEP = "protection_sweep"
RECONCILE = "protection"


class ProtectionSweep:
    def __init__(self, database: Database, queue: Any) -> None:
        self.database = database
        self.queue = queue
        self.configs = ConfigStore(database)

    def schedule(self, after: timedelta = SWEEP_EVERY) -> None:
        """Queue the next sweep unless one is already waiting."""
        with self.database.session() as s:
            waiting = s.scalar(
                select(Job.id).where(Job.kind == SWEEP, Job.status == "queued")
            )

        if waiting is None:
            self.queue.enqueue(SWEEP, {}, run_after=now() + after)

    def run(self) -> dict[str, int]:
        self.schedule()
        queued = 0

        with self.database.session() as db:
            store = ProtectionStore(db)
            apps = store.apps()
            defaults = {org: store.default(org) for org in {o for o, _ in apps}}
            wanted = [
                (org, app.id, app.registry_id)
                for org, app in apps
                if self._enforced(app.registry_id, defaults[org])
            ]

        for org, app_id, registry_id in wanted:
            self.queue.enqueue(
                RECONCILE,
                reconcile_payload(org, app_id, registry_id),
                organization_id=org,
                app_id=app_id,
                dedupe_key="reconcile",
            )
            queued += 1

        return {"apps": queued}

    def _enforced(self, registry_id: str, default: bool) -> bool:
        try:
            spec = ProtectionSpec.parse(
                (self.configs.get(registry_id) or {}).get("gitflow")
            )
        except ConfigError:
            return False

        return spec.resolved(default)


def reconcile_payload(
    organization_id: str, app_id: str, registry_id: str, action: str = "reconcile"
) -> dict[str, Any]:
    return {
        "organization_id": organization_id,
        "app_id": app_id,
        "registry_id": registry_id,
        "method": "POST",
        "path": f"apps/{registry_id}/protection",
        "body": {"action": action},
    }
