"""The organization's dashboard and a release's timeline."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.ci import CiRunRow
from app.schemas.deployments import DeploymentRow
from app.schemas.projects import PullRequestRow, ReleaseRow


class AppRef(BaseModel):
    app_id: str
    app: str
    project_id: str
    project: str


class Event(AppRef):
    kind: str
    at: Optional[datetime] = None
    title: str
    status: Optional[str] = None
    detail: Optional[str] = None
    url: Optional[str] = None


class Dashboard(BaseModel):
    apps: int
    deployments_today: dict[str, int]
    ci_today: dict[str, int]
    releases_week: int
    without_ci: list[AppRef]
    events: list[Event]


class Timeline(BaseModel):
    release: ReleaseRow
    previous: Optional[ReleaseRow] = None
    pull_requests: list[PullRequestRow]
    ci_runs: list[CiRunRow]
    deployments: list[DeploymentRow]
