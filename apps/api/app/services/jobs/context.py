"""What a job knows about the call it stands for: the organization and app it runs for, and the body enriched the way the gate would have — credentials, template sources — before the service sees it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.core.access.rules import rule_for
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Organization
from app.services.access.enrich import enrich
from app.services.access.directory import AccessDirectory


@dataclass
class JobContext:
    organization: Optional[Organization]
    app: Optional[App]
    body: dict[str, Any]
    payload: dict[str, Any]

    @property
    def registry_id(self) -> str:
        return self.payload["registry_id"]

    @classmethod
    def of(
        cls, payload: dict[str, Any], database: Database, sealer: Optional[Sealer]
    ) -> "JobContext":
        with database.session() as db:
            directory = AccessDirectory(db, sealer)
            organization = (
                db.get(Organization, payload["organization_id"])
                if payload.get("organization_id")
                else None
            )
            app = db.get(App, payload["app_id"]) if payload.get("app_id") else None
            rule = rule_for(payload.get("method", "POST"), payload["path"])
            body = dict(payload.get("body") or {})

            if rule is not None:
                body = enrich(directory, organization, app, payload["path"], body, rule)

            if app is not None:
                directory.mark_synced(app)

            return cls(organization, app, body, payload)
