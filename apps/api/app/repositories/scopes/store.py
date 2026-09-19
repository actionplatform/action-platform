"""One row per scope of an app; the derived ones are written the first time the app is looked at, so every scope has an id from then on."""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.scopes import ScopeSpec
from app.core.db.models import Scope
from app.core.shared.clock import now


class ScopeStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def for_app(self, app_id: str) -> list[Scope]:
        return list(
            self.db.scalars(
                select(Scope)
                .where(Scope.app_id == app_id)
                .order_by(Scope.created_at, Scope.name)
            )
        )

    def get(self, app_id: str, name: str) -> Optional[Scope]:
        return self.db.scalar(
            select(Scope).where(Scope.app_id == app_id, Scope.name == name)
        )

    def create(
        self,
        app_id: str,
        spec: ScopeSpec,
        created_by: Optional[str] = None,
        derived: bool = False,
    ) -> Scope:
        row = Scope(
            id=str(uuid.uuid4()),
            app_id=app_id,
            name=spec.name,
            kind=spec.kind,
            criticality=spec.criticality,
            target_kind=spec.target or None,
            target_options=json.dumps(spec.options),
            run_by=spec.run_by,
            url=spec.url,
            derived=derived,
            created_by=created_by,
            created_at=now(),
        )
        self.db.add(row)
        self.db.flush()

        return row

    def update(self, row: Scope, spec: ScopeSpec) -> Scope:
        row.kind = spec.kind
        row.criticality = spec.criticality
        row.target_kind = spec.target or None
        row.target_options = json.dumps(spec.options)
        row.run_by = spec.run_by
        row.url = spec.url
        row.derived = False
        self.db.flush()

        return row

    def delete(self, row: Scope) -> None:
        self.db.delete(row)
        self.db.flush()

    @staticmethod
    def spec_of(row: Scope) -> ScopeSpec:
        try:
            options: dict[str, Any] = json.loads(row.target_options or "{}")
        except ValueError:
            options = {}

        return ScopeSpec(
            name=row.name,
            kind=row.kind,
            criticality=row.criticality,
            target=row.target_kind or "",
            run_by=row.run_by,
            url=row.url,
            options=options,
        )

    @staticmethod
    def as_toml(spec: ScopeSpec) -> dict[str, Any]:
        item: dict[str, Any] = {
            "name": spec.name,
            "kind": spec.kind,
            "criticality": spec.criticality,
            "run_by": spec.run_by,
            **spec.options,
        }

        if spec.target:
            item["target"] = spec.target

        if spec.url:
            item["url"] = spec.url

        return item
