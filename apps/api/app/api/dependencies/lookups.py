"""Rows a route needs to find or shape before answering."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core.db.models import Organization, PullRequest, Release
from app.schemas import integrations as hosts
from app.schemas import projects
from app.schemas.common import page_bounds
from app.services.access.caller import Caller
from app.repositories.projects import ProjectsRepository


def org_dict(organization: Organization) -> dict:
    return {"id": organization.id, "name": organization.name, "slug": organization.slug}


def host_row(host) -> hosts.HostRow:
    return hosts.HostRow(
        id=host.id,
        kind=host.kind,
        name=host.name,
        base_url=host.base_url,
        username=host.username,
        default_owner=host.default_owner,
        auth_kind=host.auth_kind,
        login=host.login,
        created_at=host.created_at,
    )


def releases_page(
    db: DbSession, app_id: str, page: int, per: int
) -> projects.ReleasePage:
    page, per, offset = page_bounds(page, per)
    rows = db.scalars(
        select(Release)
        .where(Release.app_id == app_id)
        .order_by(Release.published_at.desc().nullslast(), Release.synced_at.desc())
        .offset(offset)
        .limit(per)
    ).all()
    total = db.scalar(
        select(func.count()).select_from(Release).where(Release.app_id == app_id)
    )

    return projects.ReleasePage(
        items=[
            projects.ReleaseRow.model_validate(r, from_attributes=True) for r in rows
        ],
        total=int(total or 0),
        page=page,
        per=per,
    )


def pull_requests_page(
    db: DbSession, app_id: str, page: int, per: int
) -> projects.PullRequestPage:
    page, per, offset = page_bounds(page, per)
    rows = db.scalars(
        select(PullRequest)
        .where(PullRequest.app_id == app_id)
        .order_by(PullRequest.updated_at.desc())
        .offset(offset)
        .limit(per)
    ).all()
    total = db.scalar(
        select(func.count())
        .select_from(PullRequest)
        .where(PullRequest.app_id == app_id)
    )

    return projects.PullRequestPage(
        items=[
            projects.PullRequestRow.model_validate(p, from_attributes=True)
            for p in rows
        ],
        total=int(total or 0),
        page=page,
        per=per,
    )


def imports_of(
    db: DbSession, app_id: str, errors: Optional[dict] = None
) -> projects.Imports:
    releases = db.scalars(
        select(Release)
        .where(Release.app_id == app_id)
        .order_by(Release.published_at.desc())
    ).all()
    pulls = db.scalars(
        select(PullRequest)
        .where(PullRequest.app_id == app_id)
        .order_by(PullRequest.updated_at.desc())
    ).all()

    return projects.Imports(
        releases=[
            projects.ReleaseRow.model_validate(r, from_attributes=True)
            for r in releases
        ],
        pull_requests=[
            projects.PullRequestRow.model_validate(p, from_attributes=True)
            for p in pulls
        ],
        errors=errors or {},
    )


def project_of(writes: ProjectsRepository, org: Organization, project_id: str):
    project = writes.project(org.id, project_id)

    if project is None:
        raise HTTPException(404, "project not found")

    return project


def app_of(writes: ProjectsRepository, caller: Caller, project, app_id: str):
    app = writes.app(project.id, app_id)

    if app is None or not caller.within_reach(app.id, project.id):
        raise HTTPException(404, "app not found")

    return app
