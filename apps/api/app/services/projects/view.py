"""The projects a caller sees: each with its team, the apps within reach, when it last moved and whether it is being torn down."""

from app.core.db.models import Organization, Project
from app.repositories.projects import ProjectsRepository
from app.schemas import common
from app.schemas import projects as schemas
from app.services.access.caller import Caller
from app.services.jobs import JobQueue


class ProjectView:
    def __init__(self, directory: ProjectsRepository, queue: JobQueue) -> None:
        self.directory = directory
        self.queue = queue

    def rows(
        self, caller: Caller, org: Organization, tag: bool = False
    ) -> list[schemas.ProjectRow]:
        """The organization's projects within the caller's reach; `tag` names the organization on each row."""
        tearing = self.queue.projects_being_destroyed(org.id)

        return [
            self._row(caller, org, p, tag, p.id in tearing)
            for p in self.directory.projects_of(org.id, caller.project_id)
        ]

    def across(self, caller: Caller) -> list[schemas.ProjectRow]:
        """Every project of every organization the caller belongs to, each row tagged with its organization."""
        return [
            row for o, _ in caller.organizations for row in self.rows(caller, o, True)
        ]

    def _row(
        self,
        caller: Caller,
        org: Organization,
        project: Project,
        tag: bool,
        tearing_down: bool,
    ) -> schemas.ProjectRow:
        team = self.directory.team(org.id, project.team_id) if project.team_id else None
        apps = self.directory.apps_of(project.id, caller.app_id)
        moments = [project.created_at] + [
            m for a in apps for m in (a.created_at, a.last_synced_at) if m
        ]

        return schemas.ProjectRow(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            team=common.Named(id=team.id, name=team.name) if team else None,
            apps=[
                schemas.AppInProject(
                    id=a.id,
                    name=a.name,
                    registry_id=a.registry_id,
                    source_host_id=a.source_host_id,
                    last_synced_at=a.last_synced_at,
                )
                for a in apps
            ],
            organization=common.Named(id=org.id, name=org.name) if tag else None,
            created_at=project.created_at,
            updated_at=max(moments),
            tearing_down=tearing_down,
        )
