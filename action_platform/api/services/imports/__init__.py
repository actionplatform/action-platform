"""Releases and pull requests of an app, imported from its code host into the `release` and `pull_request` tables."""

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.api.db.models import PullRequest, Release
from action_platform.api.services.credentials import Credentials
from action_platform.api.services.imports import bitbucket, github, gitlab
from action_platform.api.services.imports.common import now, parse_time
from action_platform.core.exception import ProviderError

PROVIDERS = {"github": github, "gitlab": gitlab, "bitbucket": bitbucket}


def remote_releases(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    provider = PROVIDERS.get(creds.kind)

    return provider.releases(creds, repo) if provider else []


def remote_pull_requests(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    provider = PROVIDERS.get(creds.kind)

    return provider.pull_requests(creds, repo) if provider else []


class ImportService:
    """Releases and pull requests copied from the source host into the database, so pages and agents read them without touching the provider."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    def sync_releases(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")

        remote = remote_releases(creds, repo)
        by_tag = {
            r.tag: r
            for r in self.db.scalars(select(Release).where(Release.app_id == app_id))
        }
        moment = now()

        for item in remote:
            row = by_tag.get(item["tag"])

            if row is None:
                row = Release(id=str(uuid.uuid4()), app_id=app_id)
                self.db.add(row)

            for key, value in item.items():
                setattr(row, key, value)

            row.synced_at = moment

        self.db.flush()

        return len(remote)

    def sync_pull_requests(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")

        remote = remote_pull_requests(creds, repo)
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
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> dict[str, Optional[str]]:
        errors: dict[str, Optional[str]] = {}

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


__all__ = [
    "ImportService",
    "now",
    "parse_time",
    "remote_pull_requests",
    "remote_releases",
]
