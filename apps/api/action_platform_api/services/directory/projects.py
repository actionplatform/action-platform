"""Projects and the apps inside them."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from action_platform_api.core.db.models import (
    App,
    Project,
)
from action_platform_api.core.shared.clock import now
from action_platform_api.core.shared.ids import new_id, slugify
from action_platform_api.services.directory.base import (
    DirectoryBase,
    DirectoryError,
)


class ProjectsReads(DirectoryBase):
    def projects_of(
        self, organization_id: str, project_id: Optional[str] = None
    ) -> list[Project]:
        query = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.name)
        )

        if project_id:
            query = query.where(Project.id == project_id)

        return list(self.db.scalars(query))

    def project(self, organization_id: str, project_id: str) -> Optional[Project]:
        return self.db.scalar(
            select(Project).where(
                Project.id == project_id, Project.organization_id == organization_id
            )
        )

    def apps_of(self, project_id: str, app_id: Optional[str] = None) -> list[App]:
        query = (
            select(App)
            .where(App.project_id == project_id)
            .order_by(App.created_at.desc())
        )

        if app_id:
            query = query.where(App.id == app_id)

        return list(self.db.scalars(query))

    def app(self, project_id: str, app_id: str) -> Optional[App]:
        return self.db.scalar(
            select(App).where(App.id == app_id, App.project_id == project_id)
        )

    def app_by_registry_id(self, registry_id: str) -> Optional[tuple[App, Project]]:
        row = self.db.execute(
            select(App, Project)
            .join(Project, Project.id == App.project_id)
            .where(App.registry_id == registry_id)
        ).first()

        return (row[0], row[1]) if row else None

    def registry_ids_of(
        self,
        organization_id: str,
        project_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> set[str]:
        query = (
            select(App.registry_id)
            .join(Project, Project.id == App.project_id)
            .where(Project.organization_id == organization_id)
        )

        if project_id:
            query = query.where(App.project_id == project_id)

        if app_id:
            query = query.where(App.id == app_id)

        return set(self.db.scalars(query))

    def mark_synced(self, app: App) -> None:
        app.last_synced_at = now()
        self.db.flush()

    def create_project(
        self, organization_id: str, name: str, description: str = ""
    ) -> Project:
        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        project = Project(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            slug=slugify(name),
            description=description.strip() or None,
            created_at=now(),
        )
        self.db.add(project)
        self.db.flush()

        return project

    def assign_project_team(
        self, organization_id: str, project_id: str, team_id: Optional[str]
    ) -> None:
        project = self.project(organization_id, project_id)

        if project is None:
            raise DirectoryError("project not found")

        if team_id and self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        project.team_id = team_id or None
        self.db.flush()


class ProjectsWrites(ProjectsReads):
    def delete_project(self, organization_id: str, project_id: str) -> list[str]:
        project = self.project(organization_id, project_id)

        if project is None:
            raise DirectoryError("project not found")

        registry_ids = [a.registry_id for a in self.apps_of(project.id)]
        self.db.delete(project)
        self.db.flush()

        return registry_ids

    def create_app(
        self,
        project_id: str,
        registry_id: str,
        name: str,
        source_host_id: Optional[str],
    ) -> App:
        app = App(
            id=new_id(),
            project_id=project_id,
            registry_id=registry_id,
            name=name,
            source_host_id=source_host_id,
            created_at=now(),
        )
        self.db.add(app)
        self.db.flush()

        return app

    def delete_app(self, project_id: str, app_id: str) -> Optional[App]:
        app = self.app(project_id, app_id)

        if app is None:
            return None

        self.db.delete(app)
        self.db.flush()

        return app

    def set_app_host(self, app: App, source_host_id: Optional[str]) -> None:
        app.source_host_id = source_host_id
        self.db.flush()
