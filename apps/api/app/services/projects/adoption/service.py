"""Adoption of a project's apps: where each one stands, and the job that opens their install pull requests."""

from __future__ import annotations

from typing import Any

from action_platform.core.flow.workflow import BranchError, branch_name
from action_platform.core.scaffold.installer import CI_FILES
from app.core.db.models import App, Job, Organization, Project
from app.core.errors import Invalid, NotFound
from app.repositories.projects import ProjectsRepository
from app.repositories.projects.adoption import AdoptionStore
from app.services.jobs import JobQueue

JOB_KIND = "install"


class Adoption:
    def __init__(self, directory: ProjectsRepository, queue: JobQueue) -> None:
        self.directory = directory
        self.queue = queue

    def states(self, apps: list[App]) -> list[dict[str, Any]]:
        """One row per app: `unchecked` until an install run looked at it; an open pull request the code host reports merged reads as `installed`, closed as `missing`."""
        store = AdoptionStore(self.directory.db)
        rows = store.of([a.id for a in apps])

        return [self._state(store, app, rows.get(app.id)) for app in apps]

    def _state(self, store: AdoptionStore, app: App, row: Any) -> dict[str, Any]:
        out: dict[str, Any] = {
            "app_id": app.id,
            "name": app.name,
            "registry_id": app.registry_id,
            "state": "unchecked",
            "reason": None,
            "language": None,
            "ci": None,
            "version": None,
            "branch": None,
            "pull_request": None,
            "checked_at": None,
        }

        if row is None:
            return out

        out.update(
            state=row.state,
            reason=row.reason,
            language=row.language,
            ci=row.ci,
            version=row.version,
            branch=row.branch,
            checked_at=row.checked_at,
        )

        if row.pull_request_number is not None:
            out["pull_request"] = {
                "number": row.pull_request_number,
                "url": row.pull_request_url or "",
            }

        if row.state == "pr_open":
            host = store.pull_request_state(app.id, row.pull_request_number)

            if host == "merged":
                out["state"] = "installed"
            elif host == "closed":
                out["state"] = "missing"
                out["reason"] = (
                    f"install pull request #{row.pull_request_number} was closed"
                )

        return out

    def enqueue(
        self,
        org: Organization,
        project: Project,
        apps: list[App],
        user_id: str,
        request: dict[str, Any],
    ) -> Job:
        if not apps:
            raise Invalid("no app to install on")

        ci = request.get("ci")

        if ci and ci not in CI_FILES:
            raise Invalid(f"unknown ci: {ci} (available: {', '.join(CI_FILES)})")

        try:
            branch_name("chore", request.get("code") or "")
        except BranchError as e:
            raise Invalid(str(e)) from e

        dry_run = bool(request.get("dry_run", True))
        body = {**request, "apps": [a.id for a in apps], "dry_run": dry_run}

        return self.queue.enqueue(
            JOB_KIND,
            {
                "path": f"projects/{project.id}/install",
                "method": "POST",
                "body": body,
                "registry_id": "",
                "organization_id": org.id,
                "project_id": project.id,
                "user_id": user_id,
            },
            organization_id=org.id,
            dedupe_key=None if dry_run else f"install:{project.id}",
        )

    def apps_of(self, project: Project, app_ids: list[str], reach: Any) -> list[App]:
        """The project's apps the caller reaches, or the ones named, refusing a name that is not one of them."""
        apps = [a for a in self.directory.apps_of(project.id) if reach(a)]

        if not app_ids:
            return apps

        by_id = {a.id: a for a in apps}
        unknown = [i for i in app_ids if i not in by_id]

        if unknown:
            raise NotFound(f"app not found: {', '.join(unknown)}")

        return [by_id[i] for i in dict.fromkeys(app_ids)]
