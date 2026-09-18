"""Releases and pull requests of an app, imported from its code host into the `release` and `pull_request` tables; the clone's tags land in `release` too, so every tag has a row."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ProviderError
from app.core.abc import ImportSource
from app.core.db.models import PullRequest
from app.repositories.releases.store import ReleaseStore
from app.core.shared.credentials import Credentials
from app.services.activity.imports.bitbucket import BitbucketActivity
from app.services.activity.imports.github import GithubActivity
from app.services.activity.imports.gitlab import GitlabActivity

SOURCES: dict[str, ImportSource] = {
    s.kind: s for s in (GithubActivity(), GitlabActivity(), BitbucketActivity())
}


class ActivityService:
    """Releases and pull requests copied from the source host into the database, so pages and agents read them without touching the provider."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    @staticmethod
    def source_for(creds: Credentials) -> Optional[ImportSource]:
        return SOURCES.get(creds.kind)

    def remote_releases(self, creds: Credentials, repo: str) -> list[dict[str, Any]]:
        source = self.source_for(creds)

        return source.releases(creds, repo) if source else []

    def remote_pull_requests(
        self, creds: Credentials, repo: str
    ) -> list[dict[str, Any]]:
        source = self.source_for(creds)

        return source.pull_requests(creds, repo) if source else []

    def sync_releases(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")

        remote = self.remote_releases(creds, repo)
        store = ReleaseStore(self.db)

        for item in remote:
            fields = {
                k: v for k, v in item.items() if k not in ("tag", "sha", "source")
            }
            store.ensure(
                app_id, item["tag"], item["source"], sha=item.get("sha"), **fields
            )

        return len(remote)

    def sync_tags(self, app_id: str, tags: list[dict[str, Any]]) -> int:
        """Every tag of the clone as a release row — what no host names still exists."""
        return ReleaseStore(self.db).from_tags(app_id, tags)

    def sync_pull_requests(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")

        remote = self.remote_pull_requests(creds, repo)
        by_number = {
            r.number: r
            for r in self.db.scalars(
                select(PullRequest).where(PullRequest.app_id == app_id)
            )
        }

        for item in remote:
            row = by_number.get(item["number"])

            if row is None:
                row = PullRequest(id=str(uuid.uuid4()), app_id=app_id)
                self.db.add(row)

            for key, value in item.items():
                setattr(row, key, value)

        self.db.flush()

        return len(remote)

    def sync_all(
        self,
        app_id: str,
        creds: Optional[Credentials],
        repo: Optional[str],
        tags: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Optional[str]]:
        errors: dict[str, Optional[str]] = {}

        if tags is not None:
            self.sync_tags(app_id, tags)

        for name, fn in (
            ("releases", self.sync_releases),
            ("pull_requests", self.sync_pull_requests),
        ):
            try:
                fn(app_id, creds, repo)
                errors[name] = None
            except ProviderError as e:
                errors[name] = str(e)

        return errors
