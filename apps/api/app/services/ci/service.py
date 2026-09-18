"""Runs of an app's CI job, imported into the `ci_run` table so the page reads the database, not the server."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ProviderError
from action_platform.providers.ci import build_ci_runner, embedded_ci_kind
from app.core.auth.crypto import Sealer
from app.core.db.models import App, CiRun
from app.core.shared.clock import now
from app.schemas.ci import CiLink, CiRunRow, CiRuns
from app.schemas.common import page_bounds
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.workspace.app_context import AppContext

LIMIT = 50


class CiService:
    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer],
        context: Optional[AppContext] = None,
    ) -> None:
        self.db = db
        self.directory = IntegrationsDirectory(db, sealer)
        self.context = context

    def link(self, organization_id: str, app: App) -> CiLink:
        return CiLink(
            kind=self.kind_of(organization_id, app),
            ci_host_id=app.ci_host_id,
            job=app.ci_job or "",
        )

    def sync(self, organization_id: str, app: App) -> int:
        if self.context is None:
            raise ProviderError("CI sync needs the app's workspace")

        return self.sync_runs(organization_id, app, self.context.repo_of(app))

    def page(
        self,
        organization_id: str,
        app: App,
        page: int,
        per: int,
        error: Optional[str] = None,
    ) -> CiRuns:
        page, per, offset = page_bounds(page, per)

        return CiRuns(
            link=self.link(organization_id, app),
            runs=[
                CiRunRow.model_validate(r, from_attributes=True)
                for r in self.runs(app.id, per, offset)
            ],
            error=error,
            total=self.count(app.id),
            page=page,
            per=per,
        )

    def kind_of(self, organization_id: str, app: App) -> str:
        """The runner kind of `app`: its CI host's, else the one embedded in its source host."""
        if app.ci_host_id:
            host = self.directory.ci_host(organization_id, app.ci_host_id)

            return host.kind if host else "none"

        host = (
            self.directory.host(organization_id, app.source_host_id)
            if app.source_host_id
            else None
        )

        return embedded_ci_kind(host.kind if host else None)

    def runner_for(self, organization_id: str, app: App, repo: str) -> CIRunner:
        if app.ci_host_id:
            creds = self.directory.ci_credentials_for(organization_id, app.ci_host_id)

            if creds is None:
                raise ProviderError("the app's CI host is gone; connect it again")

            return build_ci_runner(
                creds.kind,
                base_url=creds.base_url,
                token=creds.token,
                username=creds.username,
            )

        creds = self.directory.credentials_for(organization_id, app.source_host_id)
        kind = embedded_ci_kind(creds.kind if creds else None)

        return build_ci_runner(
            kind,
            base_url=creds.base_url if creds else None,
            token=creds.token if creds else None,
            repo=repo,
        )

    def sync_runs(self, organization_id: str, app: App, repo: str) -> int:
        runner = self.runner_for(organization_id, app, repo)
        remote = runner.runs(app.ci_job, LIMIT)
        by_number = {
            (r.source, r.number): r
            for r in self.db.scalars(select(CiRun).where(CiRun.app_id == app.id))
        }
        moment = now()

        for item in remote:
            row = by_number.get((runner.name, item.number))

            if row is None:
                row = CiRun(id=str(uuid.uuid4()), app_id=app.id, source=runner.name)
                self.db.add(row)

            for key, value in asdict(item).items():
                setattr(row, key, value)

            row.synced_at = moment

        self.db.flush()

        return len(remote)

    def runs(self, app_id: str, limit: int = LIMIT, offset: int = 0) -> list[CiRun]:
        return list(
            self.db.scalars(
                select(CiRun)
                .where(CiRun.app_id == app_id)
                .order_by(CiRun.number.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def count(self, app_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(CiRun).where(CiRun.app_id == app_id)
            )
            or 0
        )
