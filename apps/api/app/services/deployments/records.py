"""Deployment records: what the worker shipped, what the observed executors' pipelines shipped, and whether each version is really at its destination."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.config import Config
from action_platform.core.context import DeployResult, Run
from action_platform.core.exception import ActionPlatformError, ProviderError
from action_platform.core.targets import TargetSpec, version_from_ref
from action_platform.providers.ci import build_ci_runner
from app.core.auth.crypto import Sealer
from app.core.db.models import App, CiRun, Deployment, User
from app.core.shared.clock import now
from app.services.integrations.hosts.directory import IntegrationsDirectory

LIMIT = 50

RUN_STATUS = {
    "queued": "queued",
    "running": "running",
    "success": "success",
    "failure": "failure",
    "unstable": "failure",
    "aborted": "failure",
    "unknown": "failure",
}


class DeploymentRecords:
    def __init__(self, db: DbSession, sealer: Optional[Sealer]) -> None:
        self.db = db
        self.directory = IntegrationsDirectory(db, sealer)

    def list(self, app_id: str, limit: int = 200) -> list[Deployment]:
        return list(
            self.db.scalars(
                select(Deployment)
                .where(Deployment.app_id == app_id)
                .order_by(
                    Deployment.started_at.desc().nullslast(),
                    Deployment.synced_at.desc(),
                )
                .limit(limit)
            )
        )

    def _upsert(
        self,
        app: App,
        spec: TargetSpec,
        executor: str,
        external_ref: str,
        **fields: Any,
    ) -> Deployment:
        row = self.db.scalar(
            select(Deployment).where(
                Deployment.app_id == app.id,
                Deployment.target == spec.name,
                Deployment.executor == executor,
                Deployment.external_ref == external_ref,
            )
        )

        if row is None:
            row = Deployment(
                id=str(uuid.uuid4()),
                app_id=app.id,
                target=spec.name,
                kind=spec.kind,
                executor=executor,
                external_ref=external_ref,
            )
            self.db.add(row)

        for key, value in fields.items():
            setattr(row, key, value)

        row.synced_at = now()
        self.db.flush()

        return row

    def record_platform(
        self,
        app: App,
        config: Config,
        results: list[DeployResult],
        stage: Optional[str],
        job_id: str,
        actor: Optional[str],
        started_at: datetime,
    ) -> list[Deployment]:
        """One row per target the worker shipped to in this job."""
        specs = {t.name: t for t in config.targets}
        rows = []

        for result in results:
            spec = specs.get(result.target) or TargetSpec(result.target, result.target)
            rows.append(
                self._upsert(
                    app,
                    spec,
                    "platform",
                    job_id,
                    stage=stage,
                    version=result.version,
                    status="success" if result.ok else "failure",
                    job_id=job_id,
                    url=result.url,
                    actor=actor,
                    error=result.error,
                    started_at=started_at,
                    finished_at=now(),
                )
            )

        return rows

    def record_failure(
        self,
        app: App,
        config: Config,
        stage: Optional[str],
        version: Optional[str],
        job_id: str,
        actor: Optional[str],
        started_at: datetime,
        error: str,
    ) -> None:
        """The worker's deploy raised before any target answered: one failure per platform target, when the version is known."""
        if not version:
            return

        for spec in config.targets:
            if spec.platform:
                self._upsert(
                    app,
                    spec,
                    "platform",
                    job_id,
                    stage=stage,
                    version=version.lstrip("v"),
                    status="failure",
                    job_id=job_id,
                    actor=actor,
                    error=error[:4000],
                    started_at=started_at,
                    finished_at=now(),
                )

    def record_manual(
        self,
        app: App,
        config: Config,
        target: str,
        version: str,
        stage: Optional[str],
        url: Optional[str],
        sha: Optional[str],
        ok: bool,
        actor: Optional[str],
    ) -> Deployment:
        spec = next((t for t in config.targets if t.name == target), None)

        if spec is None:
            raise ProviderError(f"no deploy target named {target!r}")

        clean = version_from_ref(version, spec.component) or version.lstrip("v")
        moment = now()

        return self._upsert(
            app,
            spec,
            "manual",
            f"{clean}:{stage or ''}:{moment.isoformat()}",
            stage=stage,
            version=clean,
            sha=sha,
            status="success" if ok else "failure",
            url=url,
            actor=actor,
            started_at=moment,
            finished_at=moment,
        )

    def _runner(self, organization_id: str, app: App, spec: TargetSpec, repo: str):
        if spec.run_by == "github_actions":
            creds = self.directory.credentials_for(organization_id, app.source_host_id)

            if creds is None or creds.kind != "github":
                raise ProviderError(
                    f"{spec.name}: run by GitHub Actions, but the app has no GitHub source host"
                )

            return (
                build_ci_runner(
                    "github_actions",
                    repo=repo,
                    token=creds.token,
                    base_url=creds.base_url,
                ),
                spec.workflow,
            )

        if spec.run_by == "jenkins":
            creds = self.directory.ci_credentials_for(organization_id, app.ci_host_id)

            if creds is None or creds.kind != "jenkins":
                raise ProviderError(
                    f"{spec.name}: run by Jenkins, but the app is not connected to a Jenkins server"
                )

            if not spec.job:
                raise ProviderError(f"{spec.name}: a Jenkins target needs a job")

            return (
                build_ci_runner(
                    "jenkins",
                    base_url=creds.base_url,
                    token=creds.token,
                    username=creds.username,
                ),
                spec.job,
            )

        raise ProviderError(
            f"{spec.name}: nothing to observe for run_by {spec.run_by!r}"
        )

    def _ci_run_id(self, app_id: str, source: str, number: int) -> Optional[str]:
        return self.db.scalar(
            select(CiRun.id).where(
                CiRun.app_id == app_id, CiRun.source == source, CiRun.number == number
            )
        )

    def sync_observed(
        self, organization_id: str, app: App, config: Config, repo: str
    ) -> dict[str, Optional[str]]:
        """Each observed target's runs that shipped a release become deployments; then every success not yet verified is asked at the destination."""
        errors: dict[str, Optional[str]] = {}

        for spec in config.targets:
            if spec.platform or spec.run_by == "manual":
                continue

            try:
                runner, job = self._runner(organization_id, app, spec, repo)
                runs = runner.runs(job, LIMIT)
            except ActionPlatformError as e:
                errors[spec.name] = str(e)
                continue

            for run in runs:
                self._from_run(app, spec, runner.name, run)

            errors[spec.name] = None

        self.verify(app, config)

        return errors

    def _from_run(
        self, app: App, spec: TargetSpec, source: str, run: Run
    ) -> Optional[Deployment]:
        version = version_from_ref(run.branch, spec.component)

        if version is None:
            return None

        finished = (
            run.started_at + timedelta(milliseconds=run.duration_ms)
            if run.started_at and run.duration_ms
            else None
        )

        return self._upsert(
            app,
            spec,
            spec.run_by,
            f"{source}:{run.number}",
            version=version,
            sha=run.sha,
            status=RUN_STATUS.get(run.status, "failure"),
            ci_run_id=self._ci_run_id(app.id, source, run.number),
            url=run.url,
            actor=run.trigger,
            started_at=run.started_at,
            finished_at=finished,
        )

    def verify(self, app: App, config: Config) -> None:
        """Successes never verified are asked at the destination; a yes becomes `verified`."""
        pending = list(
            self.db.scalars(
                select(Deployment).where(
                    Deployment.app_id == app.id,
                    Deployment.status == "success",
                    Deployment.verified_at.is_(None),
                )
            )
        )
        targets: dict[str, Any] = {}

        for row in pending:
            if row.target not in targets:
                try:
                    targets[row.target] = config.target(row.target)
                except ActionPlatformError:
                    targets[row.target] = None

            target = targets[row.target]

            if target is None:
                continue

            try:
                there = target.verify(row.version, row.stage)
            except (NotImplementedError, ActionPlatformError):
                continue

            if there:
                row.status = "verified"
                row.verified_at = now()
                row.url = row.url or target.url(row.version, row.stage)

        self.db.flush()

    def actor_name(self, user_id: Optional[str]) -> Optional[str]:
        if not user_id:
            return None

        user = self.db.get(User, user_id)

        return user.name if user else None
