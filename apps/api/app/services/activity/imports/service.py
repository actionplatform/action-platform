"""Releases and pull requests of an app, imported from its code host into the `release` and `pull_request` tables; the clone's tags land in `release` too, so every tag has a row."""

import uuid
from dataclasses import asdict
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.abc.source_host import (
    ListsPullRequests,
    PublishesReleases,
    SourceHost,
)
from action_platform.core.context import PullRequestRow, ReleaseRow
from action_platform.core.exception import ConfigError, ProviderError
from action_platform.providers.source import build_source_host
from app.core.db.models import PullRequest
from app.repositories.releases.store import ReleaseStore
from app.core.shared.credentials import Credentials


class ActivityService:
    """Releases and pull requests copied from the source host into the database, so pages and agents read them without touching the provider."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    @staticmethod
    def source_for(creds: Credentials, repo: str) -> Optional[SourceHost]:
        """The library's provider for the host, carrying the request's token — the same class the CLI releases and opens pull requests with."""
        try:
            return build_source_host(
                creds.kind,
                repo,
                base_url=creds.base_url,
                token=creds.token,
                username=creds.username,
            )
        except ConfigError:
            return None

    def remote_releases(self, creds: Credentials, repo: str) -> list[ReleaseRow]:
        source = self.source_for(creds, repo)

        if not isinstance(source, PublishesReleases):
            return []

        return source.releases(repo)

    def remote_pull_requests(
        self, creds: Credentials, repo: str
    ) -> list[PullRequestRow]:
        source = self.source_for(creds, repo)

        if not isinstance(source, ListsPullRequests):
            return []

        return source.pull_requests(repo)

    def sync_releases(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")

        remote = self.remote_releases(creds, repo)
        store = ReleaseStore(self.db)

        for item in remote:
            store.ensure(
                app_id,
                item.tag,
                item.source,
                sha=item.sha,
                name=item.name,
                body=item.body,
                url=item.url,
                author=item.author,
                prerelease=item.prerelease,
                draft=item.draft,
                published_at=item.published_at,
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
            row = by_number.get(item.number)

            if row is None:
                row = PullRequest(id=str(uuid.uuid4()), app_id=app_id)
                self.db.add(row)

            for key, value in asdict(item).items():
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
