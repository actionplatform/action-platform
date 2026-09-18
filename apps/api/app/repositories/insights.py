"""Reads that span the contexts' tables for one organization: the day's deployments, failed runs, the week's releases, apps without CI, the latest events, and one release's timeline."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.core.db.models import (
    App,
    CiRun,
    Deployment,
    Project,
    PullRequest,
    Release,
    SourceHost,
)
from app.core.shared.clock import now

EMBEDDED_CI_HOSTS = ("github", "gitlab", "bitbucket")


class Insights:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def _apps(
        self, organization_id: str, project_id: Optional[str], app_id: Optional[str]
    ):
        query = (
            select(
                App.id,
                App.name,
                Project.id,
                Project.name,
                App.source_host_id,
                App.ci_host_id,
            )
            .join(Project, Project.id == App.project_id)
            .where(Project.organization_id == organization_id)
        )

        if project_id:
            query = query.where(Project.id == project_id)

        if app_id:
            query = query.where(App.id == app_id)

        return list(self.db.execute(query))

    def dashboard(
        self,
        organization_id: str,
        project_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> dict[str, Any]:
        apps = self._apps(organization_id, project_id, app_id)
        ids = [a[0] for a in apps]
        names = {
            a[0]: {"app_id": a[0], "app": a[1], "project_id": a[2], "project": a[3]}
            for a in apps
        }
        moment = now()
        today = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        week = moment - timedelta(days=7)

        if not ids:
            return {
                "apps": 0,
                "deployments_today": {},
                "ci_today": {},
                "releases_week": 0,
                "without_ci": [],
                "events": [],
            }

        deployments = {
            status: int(count)
            for status, count in self.db.execute(
                select(Deployment.status, func.count())
                .where(Deployment.app_id.in_(ids), Deployment.started_at >= today)
                .group_by(Deployment.status)
            )
        }
        ci = {
            status: int(count)
            for status, count in self.db.execute(
                select(CiRun.status, func.count())
                .where(CiRun.app_id.in_(ids), CiRun.started_at >= today)
                .group_by(CiRun.status)
            )
        }
        releases = int(
            self.db.scalar(
                select(func.count())
                .select_from(Release)
                .where(Release.app_id.in_(ids), Release.published_at >= week)
            )
            or 0
        )
        hosts = {
            h.id: h.kind
            for h in self.db.scalars(
                select(SourceHost).where(SourceHost.organization_id == organization_id)
            )
        }
        without_ci = [
            names[a[0]]
            for a in apps
            if not a[5] and hosts.get(a[4] or "", "") not in EMBEDDED_CI_HOSTS
        ]

        return {
            "apps": len(ids),
            "deployments_today": deployments,
            "ci_today": ci,
            "releases_week": releases,
            "without_ci": without_ci,
            "events": self._events(ids, names),
        }

    def _events(
        self, ids: list[str], names: dict[str, dict], limit: int = 12
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for d in self.db.scalars(
            select(Deployment)
            .where(Deployment.app_id.in_(ids))
            .order_by(Deployment.synced_at.desc())
            .limit(limit)
        ):
            events.append(
                {
                    **names[d.app_id],
                    "kind": "deployment",
                    "at": d.finished_at or d.started_at or d.synced_at,
                    "title": f"{d.target} {d.version}",
                    "status": d.status,
                    "detail": d.stage,
                    "url": d.url,
                }
            )

        for r in self.db.scalars(
            select(Release)
            .where(Release.app_id.in_(ids))
            .order_by(Release.synced_at.desc())
            .limit(limit)
        ):
            events.append(
                {
                    **names[r.app_id],
                    "kind": "release",
                    "at": r.published_at or r.synced_at,
                    "title": r.tag,
                    "status": "prerelease" if r.prerelease else "release",
                    "detail": r.name,
                    "url": r.url,
                }
            )

        for p in self.db.scalars(
            select(PullRequest)
            .where(PullRequest.app_id.in_(ids))
            .order_by(PullRequest.updated_at.desc())
            .limit(limit)
        ):
            events.append(
                {
                    **names[p.app_id],
                    "kind": "pull_request",
                    "at": p.merged_at or p.updated_at,
                    "title": f"#{p.number} {p.title}",
                    "status": p.state,
                    "detail": f"{p.head} → {p.base}",
                    "url": p.url,
                }
            )

        for c in self.db.scalars(
            select(CiRun)
            .where(CiRun.app_id.in_(ids))
            .order_by(CiRun.synced_at.desc())
            .limit(limit)
        ):
            events.append(
                {
                    **names[c.app_id],
                    "kind": "ci_run",
                    "at": c.started_at or c.synced_at,
                    "title": c.name or f"#{c.number}",
                    "status": c.status,
                    "detail": c.branch,
                    "url": c.url,
                }
            )

        events.sort(key=lambda e: e["at"] or datetime.min, reverse=True)

        return events[:limit]

    def timeline(self, app_id: str, tag: str) -> Optional[dict[str, Any]]:
        release = self.db.scalar(
            select(Release).where(Release.app_id == app_id, Release.tag == tag)
        )

        if release is None:
            return None

        anchor = release.published_at or release.synced_at
        previous = self.db.scalar(
            select(Release)
            .where(
                Release.app_id == app_id,
                Release.component == release.component,
                Release.id != release.id,
                or_(
                    Release.published_at < anchor,
                    and_(Release.published_at.is_(None), Release.synced_at < anchor),
                ),
            )
            .order_by(Release.published_at.desc().nullslast(), Release.synced_at.desc())
        )
        since = (previous.published_at or previous.synced_at) if previous else None
        pulls_query = select(PullRequest).where(
            PullRequest.app_id == app_id,
            PullRequest.state == "merged",
            PullRequest.merged_at <= anchor,
        )

        if since is not None:
            pulls_query = pulls_query.where(PullRequest.merged_at > since)

        pulls = list(
            self.db.scalars(
                pulls_query.order_by(PullRequest.merged_at.desc()).limit(50)
            )
        )
        runs = list(
            self.db.scalars(
                select(CiRun)
                .where(
                    CiRun.app_id == app_id,
                    or_(
                        CiRun.branch == tag,
                        CiRun.branch == release.version,
                        and_(CiRun.sha.is_not(None), CiRun.sha == release.sha),
                    ),
                )
                .order_by(CiRun.number.desc())
                .limit(20)
            )
        )
        deployments = list(
            self.db.scalars(
                select(Deployment)
                .where(
                    Deployment.app_id == app_id,
                    or_(
                        Deployment.release_id == release.id,
                        Deployment.version == release.version,
                    ),
                )
                .order_by(Deployment.started_at.desc().nullslast())
            )
        )

        return {
            "release": release,
            "previous": previous,
            "pull_requests": pulls,
            "ci_runs": runs,
            "deployments": deployments,
        }
