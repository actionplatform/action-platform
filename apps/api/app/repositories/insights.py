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
    DeploymentEvent,
    Project,
    ProtectionEvent,
    PullRequest,
    Release,
    SourceHost,
)
from app.core.shared.clock import now

EMBEDDED_CI_HOSTS = ("github", "gitlab", "bitbucket")
ACTIVE_DEPLOYMENT = (
    "queued",
    "running",
    "paused",
    "awaiting_approval",
    "rolling_back",
)
EVENT_KINDS = ("deployment", "release", "pull_request", "ci_run", "protection")


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

    def in_progress(
        self,
        organization_id: str,
        project_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Deployments still queued or running, the latest started first."""
        names = {
            a[0]: {"app_id": a[0], "app": a[1], "project_id": a[2], "project": a[3]}
            for a in self._apps(organization_id, project_id, app_id)
        }

        if not names:
            return []

        return [
            {
                **names[d.app_id],
                "id": d.id,
                "target": d.target,
                "kind": d.kind,
                "stage": d.stage,
                "version": d.version,
                "status": d.status,
                "started_at": d.started_at,
                "url": d.url,
            }
            for d in self.db.scalars(
                select(Deployment)
                .where(
                    Deployment.app_id.in_(list(names)),
                    Deployment.status.in_(ACTIVE_DEPLOYMENT),
                )
                .order_by(
                    Deployment.started_at.desc().nullslast(),
                    Deployment.synced_at.desc(),
                )
                .limit(100)
            )
        ]

    def app_events(
        self,
        organization_id: str,
        project_id: str,
        app_id: str,
        kinds: tuple[str, ...] = EVENT_KINDS,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """The latest events of one app, newest first, only of `kinds`."""
        apps = self._apps(organization_id, project_id, app_id)
        names = {
            a[0]: {"app_id": a[0], "app": a[1], "project_id": a[2], "project": a[3]}
            for a in apps
        }

        if not names:
            return []

        return self._events(list(names), names, limit, kinds)

    def _events(
        self,
        ids: list[str],
        names: dict[str, dict],
        limit: int = 12,
        kinds: tuple[str, ...] = EVENT_KINDS,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        if "deployment" in kinds:
            for d in self.db.scalars(
                select(Deployment)
                .where(Deployment.app_id.in_(ids))
                .order_by(
                    func.coalesce(
                        Deployment.finished_at,
                        Deployment.started_at,
                        Deployment.synced_at,
                    ).desc()
                )
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

            for e in self.db.scalars(
                select(DeploymentEvent)
                .where(DeploymentEvent.app_id.in_(ids))
                .order_by(DeploymentEvent.at.desc())
                .limit(limit)
            ):
                events.append(
                    {
                        **names[e.app_id],
                        "kind": "deployment",
                        "at": e.at,
                        "title": e.title,
                        "status": e.kind,
                        "detail": " · ".join(x for x in (e.detail, e.actor) if x),
                        "url": None,
                    }
                )

        if "release" in kinds:
            for r in self.db.scalars(
                select(Release)
                .where(Release.app_id.in_(ids))
                .order_by(func.coalesce(Release.published_at, Release.synced_at).desc())
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

        if "pull_request" in kinds:
            for p in self.db.scalars(
                select(PullRequest)
                .where(PullRequest.app_id.in_(ids))
                .order_by(
                    func.coalesce(PullRequest.merged_at, PullRequest.updated_at).desc()
                )
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

        if "ci_run" in kinds:
            for c in self.db.scalars(
                select(CiRun)
                .where(CiRun.app_id.in_(ids))
                .order_by(func.coalesce(CiRun.started_at, CiRun.synced_at).desc())
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

        if "protection" in kinds:
            for p in self.db.scalars(
                select(ProtectionEvent)
                .where(ProtectionEvent.app_id.in_(ids))
                .order_by(ProtectionEvent.at.desc())
                .limit(limit)
            ):
                events.append(
                    {
                        **names[p.app_id],
                        "kind": "protection",
                        "at": p.at,
                        "title": p.title,
                        "status": p.kind,
                        "detail": " · ".join(x for x in (p.detail, p.actor) if x),
                        "url": None,
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
