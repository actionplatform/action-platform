"""Host projects → platform projects; the repositories linked to a project become its apps."""

from typing import Optional

from action_platform.api.db.models import Project
from action_platform.api.services.directory import DirectoryError
from action_platform.api.services.organization_import.step import ImportStep


class ProjectImporter(ImportStep):
    def run(self, login: str, wanted: dict[int, Optional[str]]) -> dict[str, Project]:
        """Returns owner/name (lowercase) → the platform project a repository belongs to through a wanted host project. `wanted` maps the host project number to the platform project its apps go into, or None for one named after it."""
        targets: dict[str, Project] = {}

        if not wanted:
            return targets

        for remote in self.host.projects(login):
            if remote["number"] not in wanted:
                continue

            project = self._target_for(remote, wanted[remote["number"]])

            for repo in remote["repositories"]:
                targets.setdefault(repo.lower(), project)

        self.ctx.db.commit()

        return targets

    def _target_for(self, remote: dict, chosen: Optional[str]) -> Project:
        if chosen:
            project = self.writes.project(self.organization_id, chosen)

            if project is None:
                raise DirectoryError(f"project {chosen} not found")

            self.summary.skip(
                f"project {remote['title']}", f"apps added to {project.name}"
            )

            return project

        project = self.ctx.project_named(remote["title"])

        if project is not None:
            self.summary.skip(
                f"project {remote['title']}", "already exists, apps added to it"
            )

            return project

        project = self.writes.create_project(
            self.organization_id, remote["title"], remote.get("description") or ""
        )
        self.summary.projects.append(project.name)

        return project
