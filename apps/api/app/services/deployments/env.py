"""What the platform tells a deploy target that the repository need not: the app's `org/project/app` and the organization's plugin options — `AP_APP`, `AP_<SLUG>_<KEY>` — with the platform-wide defaults underneath."""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select

from app.core.db.database import Database
from app.core.db.models import App, Organization, PluginOption, Project


class DeployEnv:
    def __init__(self, database: Database) -> None:
        self.database = database

    def for_app(
        self, organization: Optional[Organization], app: Optional[App]
    ) -> dict[str, str]:
        if organization is None or app is None:
            return {}

        with self.database.session() as db:
            project = db.get(Project, app.project_id)
            rows = db.scalars(
                select(PluginOption).where(
                    PluginOption.organization_id.in_({"", organization.id})
                )
            ).all()

        env = {
            "AP_APP": f"{organization.slug}/{project.slug if project else ''}/{app.name}",
        }

        for row in sorted(rows, key=lambda r: r.organization_id != ""):
            value = json.loads(row.value)

            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                name = f"AP_{row.plugin}_{row.key}".upper().replace("-", "_")
                env[name] = str(value)

        return env
