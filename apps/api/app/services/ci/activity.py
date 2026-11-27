"""What the organization's CI servers are doing now: the runs waiting and why, the executors and what each runs. A job that is no app of the caller's stays anonymous."""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App, CiHost, Project
from app.repositories.projects import ProjectsRepository
from app.schemas import ci as schemas
from app.services.ci.pipelines import Pipelines

Reach = Callable[[App, Project], bool]
T = TypeVar("T")


def answer(read: Callable[[], T]) -> Optional[T]:
    """What the server answered; None when its runner cannot tell, while a failure reaches the caller."""
    try:
        return read()
    except NotImplementedError:
        return None


def owner_of(
    job: Optional[str], known: dict[str, schemas.CiAppRef]
) -> Optional[schemas.CiAppRef]:
    """The app whose job this is — the job itself, or a branch under it (a multibranch job's `app/main`)."""
    if not job:
        return None

    name = job

    while name:
        if name in known:
            return known[name].model_copy(update={"job": job})

        name = name.rpartition("/")[0]

    return None


class CiActivity:
    def __init__(self, pipelines: Pipelines, projects: ProjectsRepository) -> None:
        self.pipelines = pipelines
        self.projects = projects

    def known_jobs(
        self, organization_id: str, host: CiHost, reach: Reach
    ) -> dict[str, schemas.CiAppRef]:
        known: dict[str, schemas.CiAppRef] = {}

        for project in self.projects.projects_of(organization_id):
            for app in self.projects.apps_of(project.id):
                if app.ci_host_id != host.id or not reach(app, project):
                    continue

                for job in self.pipelines.jobs(organization_id, app, host.kind):
                    if job.name:
                        known.setdefault(
                            job.name,
                            schemas.CiAppRef(
                                project_id=project.id,
                                app_id=app.id,
                                name=app.name,
                                job=job.name,
                            ),
                        )

        return known

    def of(self, organization_id: str, reach: Reach) -> schemas.CiActivity:
        hosts = self.pipelines.ci.directory.ci_hosts_of(organization_id)

        return schemas.CiActivity(
            hosts=[self.host(organization_id, h, reach) for h in hosts]
        )

    def host(
        self, organization_id: str, host: CiHost, reach: Reach
    ) -> schemas.CiHostActivity:
        row = schemas.CiHostActivity(id=host.id, name=host.name, kind=host.kind)

        try:
            runner: CIRunner = self.pipelines.ci.host_runner(organization_id, host.id)
            queue = answer(runner.queue)
            executors = answer(runner.executors)
        except ActionPlatformError as e:
            row.error = str(e)

            return row

        known = self.known_jobs(organization_id, host, reach)

        if queue is not None:
            row.queue = []

            for item in queue:
                app = owner_of(item.job, known)
                row.queue.append(
                    schemas.CiQueueRow(
                        since=item.since,
                        why=item.why if app else None,
                        app=app,
                    )
                )

        if executors is not None:
            row.executors = []

            for slot in executors:
                app = owner_of(slot.job, known) if slot.busy else None
                row.executors.append(
                    schemas.CiExecutorRow(
                        node=slot.node,
                        busy=slot.busy,
                        number=slot.number if app else None,
                        app=app,
                    )
                )

        return row
