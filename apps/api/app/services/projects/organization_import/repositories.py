"""Repositories → one project with one app each."""

import logging
from typing import Any, Optional

from action_platform.core.exception import ActionPlatformError
from app.core.db.models import Project
from app.core.shared import git_auth as auth
from app.schemas import SourceCredentials
from app.services.activity import ActivityService
from app.services.directory import Credentials, DirectoryError
from app.services.projects.organization_import.step import ImportStep
from app.services.workspace.checkout import Workspaces

log = logging.getLogger("action_platform.import")


class RepositoryImporter(ImportStep):
    def run(
        self,
        creds: Credentials,
        host_id: str,
        login: str,
        wanted: set[str],
        into: Optional[Project] = None,
        targets: Optional[dict[str, Project]] = None,
    ) -> dict[str, Project]:
        """Returns owner/name (lowercase) → project for every wanted repository that exists on the platform afterwards. A repository goes into its host project's platform project (`targets`), else into `into`, else into a project of its own."""
        projects: dict[str, Project] = {}
        targets = targets or {}

        if not wanted:
            return projects

        known = self.ctx.known_repositories()
        credentials = self._credentials(creds)
        seen: set[str] = set()

        for repo in self.host.repositories(login):
            key = repo["full_name"].lower()

            if key not in wanted:
                continue

            seen.add(key)

            if key in known:
                self.summary.skip(
                    repo["full_name"], f"already imported as {known[key]}"
                )
                project = self.ctx.project_named(known[key])

                if project is not None:
                    projects[key] = project

                continue

            target = targets.get(key, into)
            project = self._import_one(repo, credentials, host_id, target)

            if project is None:
                continue

            projects[key] = project

            if target is None:
                self.summary.projects.append(project.name)
            else:
                self.summary.apps.append(f"{repo['name']} → {project.name}")

            self.ctx.db.commit()

        for key in sorted(wanted - seen):
            self.summary.skip(key, "not found on the host")

        return projects

    def _credentials(self, creds: Credentials) -> SourceCredentials:
        name, email = self.writes.git_author_of(self.organization_id)

        return SourceCredentials(
            **{**creds.as_dict(), "author_name": name, "author_email": email}
        )

    def _import_one(
        self,
        repo: dict[str, Any],
        credentials: SourceCredentials,
        host_id: str,
        into: Optional[Project],
    ) -> Optional[Project]:
        try:
            return self._register(repo, credentials, host_id, into)
        except (ActionPlatformError, DirectoryError) as e:
            self.summary.skip(repo["full_name"], str(e))
        except Exception as e:
            log.exception("import of %s failed", repo["full_name"])
            self.summary.skip(repo["full_name"], str(e))

        return None

    def _register(
        self,
        repo: dict[str, Any],
        credentials: SourceCredentials,
        host_id: str,
        into: Optional[Project],
    ) -> Project:
        with auth.git_auth(credentials):
            entry = Workspaces(self.ctx.registry).adopt(
                repo["url"], repo["name"], require_manifest=False
            )

        project = (
            into
            or self.ctx.project_named(repo["name"])
            or self.writes.create_project(
                self.organization_id, repo["name"], repo.get("description") or ""
            )
        )
        app = self.writes.create_app(project.id, entry.id, entry.name, host_id)
        ActivityService(self.ctx.db).sync_all(
            app.id,
            self.writes.credentials_for(self.organization_id, host_id),
            repo["full_name"],
        )

        return project
