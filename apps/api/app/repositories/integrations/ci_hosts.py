"""The CI servers an organization connected: Jenkins and the like, each with its own token."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.core.db.models import CiHost
from app.core.shared.clock import now
from app.core.shared.credentials import Credentials
from app.core.shared.ids import new_id
from app.repositories.base import (
    CI_HOST_KINDS,
    CI_HOST_LABELS,
    DirectoryBase,
    DirectoryError,
)


class CiHostsReads(DirectoryBase):
    def ci_hosts_of(self, organization_id: str) -> list[CiHost]:
        return list(
            self.db.scalars(
                select(CiHost)
                .where(CiHost.organization_id == organization_id)
                .order_by(CiHost.created_at)
            )
        )

    def ci_host(self, organization_id: str, id: str) -> Optional[CiHost]:
        return self.db.scalar(
            select(CiHost).where(
                CiHost.id == id, CiHost.organization_id == organization_id
            )
        )

    def ci_credentials_for(
        self, organization_id: str, id: Optional[str]
    ) -> Optional[Credentials]:
        if not id or self.sealer is None:
            return None

        host = self.ci_host(organization_id, id)

        if host is None:
            return None

        return Credentials(
            kind=host.kind,
            token=self.sealer.open(host.token_encrypted),
            username=host.username,
            base_url=host.base_url,
            owner=None,
        )


class CiHostsWrites(CiHostsReads):
    def add_ci_host(
        self,
        organization_id: str,
        kind: str,
        name: str,
        base_url: str,
        token: str,
        username: Optional[str] = None,
    ) -> CiHost:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        if kind not in CI_HOST_KINDS:
            raise DirectoryError("unknown ci kind")

        if not base_url.strip():
            raise DirectoryError("base_url is required")

        if not token.strip():
            raise DirectoryError("token is required")

        host = CiHost(
            id=new_id(),
            organization_id=organization_id,
            kind=kind,
            name=name.strip() or CI_HOST_LABELS[kind],
            base_url=base_url.strip().rstrip("/"),
            username=(username or "").strip() or None,
            token_encrypted=self.sealer.seal(token.strip()),
            created_at=now(),
        )
        self.db.add(host)
        self.db.flush()

        return host

    def remove_ci_host(self, organization_id: str, id: str) -> None:
        host = self.ci_host(organization_id, id)

        if host is None:
            raise DirectoryError("ci host not found")

        self.db.delete(host)
        self.db.flush()
