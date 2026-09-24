"""App › Releases › Readiness: can this release reach this stage? The core's checks on the app's clone at the tag, stored per release and stage, and the gate a deploy passes through."""

from __future__ import annotations

from typing import Any, Callable, Optional

from action_platform.core.facade import ActionPlatform
from action_platform.core.context import Check
from app.core.db.database import Database
from app.core.db.models import App, Release
from app.core.errors import Conflict, NotFound
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.releases import ReadinessStore, ReleaseStore, tag_of, verdict
from app.repositories.workspace.registry import Registry
from app.schemas import SourceCredentials
from app.services.jobs import JobQueue
from app.services.workspace import Workspaces
from app.services.workspace import git_auth as auth


class ReadinessService:
    def __init__(
        self,
        registry: Registry,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        configs: ConfigStore | None = None,
        credentials: SourceCredentials | None = None,
    ) -> None:
        self.registry = registry
        self.identity = identity
        self.env = env
        self.configs = configs or ConfigStore(registry.store.database)
        self.credentials = credentials

    def check(
        self,
        id: str,
        tag: str,
        stage: str,
        shape: Optional[str] = None,
        scopes: Optional[list[dict[str, Any]]] = None,
    ) -> list[Check]:
        _, root = Workspaces(self.registry).checkout(id)
        config = auth.apply(self.configs.config(id, root), self.credentials)

        if scopes:
            config._scopes_spec = scopes

        tool = ActionPlatform(
            config=config,
            repo_root=root,
            identity=self.identity,
            env=self.env,
        )

        return tool.check_readiness(stage, version=tag, shape=shape)


class ReadinessRequests:
    """What the API does with readiness: queue a check per stage, read what the worker stored, refuse a deploy the checks failed."""

    def __init__(self, database: Database, queue: JobQueue) -> None:
        self.database = database
        self.queue = queue

    def release_of(self, app: App, tag: str) -> tuple[str, str]:
        with self.database.session() as db:
            release = ReleaseStore(db).get(app.id, tag)

            if release is None:
                raise NotFound(f"no release {tag}")

            return release.id, release.tag

    def request(
        self,
        organization_id: str,
        app: App,
        release_id: str,
        tag: str,
        stages: tuple[str, ...],
        user_id: Any = None,
        manages: bool = False,
    ) -> list[str]:
        ids: list[str] = []

        for stage in stages:
            job = self.queue.enqueue(
                "readiness",
                {
                    "path": f"apps/{app.registry_id}/readiness",
                    "method": "POST",
                    "body": {"tag": tag, "stage": stage},
                    "registry_id": app.registry_id,
                    "organization_id": organization_id,
                    "app_id": app.id,
                    "release_id": release_id,
                    "user_id": user_id,
                    "manages": manages,
                },
                organization_id=organization_id,
                app_id=app.id,
                dedupe_key=f"readiness:{tag}:{stage}",
            )
            ids.append(job.id)

            with self.database.session() as db:
                release = db.get(Release, release_id)

                if release is None:
                    raise NotFound(f"no release {tag}")

                ReadinessStore(db).queued(release, stage, job.id)

        return ids

    def of(self, app: App, tag: str) -> list[dict[str, Any]]:
        with self.database.session() as db:
            release = ReleaseStore(db).get(app.id, tag)

            if release is None:
                raise NotFound(f"no release {tag}")

            store = ReadinessStore(db)

            return [self.view(row) for row in store.for_release(release.id)]

    @staticmethod
    def view(row: Any) -> dict[str, Any]:
        return {
            "stage": row.stage,
            "status": row.status,
            "verdict": verdict(row),
            "ok": row.ok,
            "checks": ReadinessStore.checks_of(row),
            "job_id": row.job_id,
            "checked_at": row.checked_at,
            "updated_at": row.updated_at,
        }

    def assert_deployable(
        self, app: App, version: Optional[str], stage: str, force: bool
    ) -> None:
        """A deploy of a release whose readiness for `stage` failed is refused unless forced; a release never checked, or still being checked, passes."""
        if force or not version:
            return

        with self.database.session() as db:
            releases = ReleaseStore(db)
            release = releases.get(app.id, version) or releases.get(
                app.id, tag_of("", version.lstrip("v"))
            )

            if release is None:
                return

            row = ReadinessStore(db).get(release.id, stage)

            if row is None or verdict(row) != "blocked":
                return

            blocking = [
                c
                for c in ReadinessStore.checks_of(row)
                if not c.get("ok") and c.get("severity", "error") == "error"
            ]
            reasons = "; ".join(
                f"{c.get('id')}: {c.get('detail')}" for c in blocking[:3]
            )

            raise Conflict(
                f"{release.tag} is not deployable to {stage} — {reasons}. Fix it and re-check, or force the deploy."
            )
