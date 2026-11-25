from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db.models import (
    App,
    AppProtection,
    Project,
    ProtectionDefault,
    ProtectionEvent,
)
from app.core.shared.clock import now
from app.core.shared.ids import new_id


class ProtectionStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def default(self, organization_id: str) -> bool:
        row = self.db.get(ProtectionDefault, organization_id)

        return bool(row and row.enforce)

    def set_default(self, organization_id: str, enforce: bool) -> None:
        row = self.db.get(ProtectionDefault, organization_id)

        if row is None:
            row = ProtectionDefault(organization_id=organization_id)
            self.db.add(row)

        row.enforce = enforce
        row.updated_at = now()
        self.db.flush()

    def of(self, app_id: str) -> Optional[AppProtection]:
        return self.db.get(AppProtection, app_id)

    def state(self, app_id: str) -> Optional[dict[str, Any]]:
        row = self.of(app_id)

        return json.loads(row.state) if row and row.state else None

    def save(
        self,
        app_id: str,
        state: dict[str, Any],
        enforced: bool,
        applied: bool = False,
    ) -> AppProtection:
        row = self.of(app_id)
        moment = now()

        if row is None:
            row = AppProtection(app_id=app_id)
            self.db.add(row)

        row.state = json.dumps(state)
        row.enforced = enforced
        row.checked_at = moment
        row.updated_at = moment

        if applied:
            row.applied_at = moment

        self.db.flush()

        return row

    def record(
        self,
        app_id: str,
        kind: str,
        title: str,
        detail: Optional[str] = None,
        actor: Optional[str] = None,
        at: Optional[datetime] = None,
    ) -> ProtectionEvent:
        event = ProtectionEvent(
            id=new_id(),
            app_id=app_id,
            kind=kind,
            title=title,
            detail=detail,
            actor=actor,
            at=at or now(),
        )
        self.db.add(event)
        self.db.flush()

        return event

    def apps(self) -> list[tuple[str, App]]:
        """Every app with its organization, for the sweep."""
        return [
            (organization_id, app)
            for app, organization_id in self.db.execute(
                select(App, Project.organization_id).join(
                    Project, Project.id == App.project_id
                )
            )
        ]
