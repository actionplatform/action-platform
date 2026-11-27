"""The CI server an app is connected to, as a runner with its own credentials — what a deploy starts a dispatched target of a CI server with, through the runner its plugin registers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.abc.ci_runner import CIRunner
from action_platform.providers.ci import build_ci_runner
from app.core.auth.crypto import Sealer
from app.core.db.models import App, Project
from app.services.integrations.hosts.directory import IntegrationsDirectory


class AppCiRunners:
    def __init__(self, db: DbSession, sealer: Optional[Sealer]) -> None:
        self.db = db
        self.directory = IntegrationsDirectory(db, sealer)

    def of(self, app: Optional[App]) -> list[CIRunner]:
        if app is None or not app.ci_host_id:
            return []

        project = self.db.get(Project, app.project_id)

        if project is None:
            return []

        creds = self.directory.ci_credentials_for(
            project.organization_id, app.ci_host_id
        )

        if creds is None:
            return []

        return [
            build_ci_runner(
                creds.kind,
                base_url=creds.base_url,
                token=creds.token,
                username=creds.username,
            )
        ]

    def of_registry(self, registry_id: str) -> list[CIRunner]:
        return self.of(
            self.db.scalar(select(App).where(App.registry_id == registry_id))
        )
