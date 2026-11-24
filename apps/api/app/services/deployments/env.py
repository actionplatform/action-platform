"""What the platform tells a deploy target that the repository need not: the app's `org/project/app` and, per plugin, the options of its one connection — `AP_APP`, `AP_<SLUG>_<KEY>` — the organization's own, or the platform's when `AP_PLATFORM_CONNECTIONS` grants it."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from action_platform.core.exception import ConfigError
from app.core.db.database import Database
from app.core.auth.crypto import Sealer
from app.core.db.models import App, Organization, PluginOption, Project
from app.services.integrations.plugins.connections import (
    ConnectionGuard,
    SharedConnections,
    env_name,
    owner_of,
)
from app.services.integrations.plugins.options import decode


class DeployEnv:
    def __init__(
        self,
        database: Database,
        sealer: Optional[Sealer] = None,
        policy: Optional[SharedConnections] = None,
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.policy = policy

    def for_app(
        self, organization: Optional[Organization], app: Optional[App]
    ) -> dict[str, str]:
        return self.connections(organization, app).env

    def of_registry(self, registry_id: str) -> ConnectionGuard:
        with self.database.session() as db:
            app = db.scalar(select(App).where(App.registry_id == registry_id))
            project = db.get(Project, app.project_id) if app is not None else None
            organization = (
                db.get(Organization, project.organization_id)
                if project is not None
                else None
            )

        return self.connections(organization, app)

    def connections(
        self, organization: Optional[Organization], app: Optional[App]
    ) -> ConnectionGuard:
        """The deploy environment of `app` and the guard its targets pass: nothing from another organization, nothing from the platform the policy does not grant."""
        policy = self.policy or SharedConnections.from_settings()

        if organization is None or app is None:
            return ConnectionGuard({}, False)

        with self.database.session() as db:
            project = db.get(Project, app.project_id)

            if project is None or project.organization_id != organization.id:
                raise ConfigError(
                    f"app {app.name} does not belong to organization {organization.slug}"
                )

            slugs = db.scalars(
                select(PluginOption.plugin)
                .where(PluginOption.organization_id.in_({"", organization.id}))
                .distinct()
            ).all()
            rows: list[PluginOption] = []

            for slug in sorted(slugs):
                owner = owner_of(db, slug, organization.id, policy)

                if owner is not None:
                    rows += db.scalars(
                        select(PluginOption).where(
                            PluginOption.plugin == slug,
                            PluginOption.organization_id == owner,
                        )
                    ).all()

        env = {
            "AP_APP": f"{organization.slug}/{project.slug}/{app.name}",
        }

        for row in rows:
            value = decode(row.value, self.sealer)

            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                env[env_name(row.plugin, row.key)] = str(value)

        return ConnectionGuard(env, policy.allows(organization))
