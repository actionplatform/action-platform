"""Projects and the apps registered in them (teams are read to say who may reach a project)."""

from app.repositories.organization.teams import TeamsReads
from app.repositories.projects.projects import ProjectsReads, ProjectsWrites


class ProjectsRepository(ProjectsWrites, ProjectsReads, TeamsReads):
    pass


__all__ = ["ProjectsRepository"]
