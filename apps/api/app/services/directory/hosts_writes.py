"""Code hosts connected to an organization, written: add, connect through OAuth, remove, rotate the token, set the owner."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.core.db.models import (
    SourceHost,
)
from app.core.shared.clock import now
from app.core.shared.ids import new_id
from app.services.directory.base import (
    HOST_KINDS,
    HOST_LABELS,
    DirectoryError,
)
from app.services.directory.hosts_reads import HostsReads


class HostsWrites(HostsReads):
    def host(self, organization_id: str, host_id: str) -> Optional[SourceHost]:
        return self.db.scalar(
            select(SourceHost).where(
                SourceHost.id == host_id, SourceHost.organization_id == organization_id
            )
        )

    def add_host(
        self,
        organization_id: str,
        kind: str,
        name: str,
        token: str,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        default_owner: Optional[str] = None,
    ) -> SourceHost:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        if kind not in HOST_KINDS:
            raise DirectoryError("unknown host kind")

        if not token.strip():
            raise DirectoryError("token is required")

        host = SourceHost(
            id=new_id(),
            organization_id=organization_id,
            kind=kind,
            name=name.strip() or HOST_LABELS[kind],
            base_url=(base_url or "").strip() or None,
            username=(username or "").strip() or None,
            token_encrypted=self.sealer.seal(token.strip()),
            default_owner=(default_owner or "").strip() or None,
            auth_kind="token",
            created_at=now(),
        )
        self.db.add(host)
        self.db.flush()

        return host

    def connect_oauth_host(
        self,
        organization_id: str,
        provider: str,
        login: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        base_url: Optional[str],
        owner: Optional[str] = None,
    ) -> SourceHost:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        host = self.db.scalar(
            select(SourceHost).where(
                SourceHost.organization_id == organization_id,
                SourceHost.kind == provider,
                SourceHost.auth_kind == "oauth",
                SourceHost.login == login,
            )
        )

        if host is None:
            host = SourceHost(
                id=new_id(),
                organization_id=organization_id,
                kind=provider,
                name=f"{HOST_LABELS[provider]} · {login}",
                username="x-token-auth" if provider == "bitbucket" else None,
                default_owner=owner or login,
                auth_kind="oauth",
                login=login,
                token_encrypted="",
                created_at=now(),
            )
            self.db.add(host)
        elif owner:
            host.default_owner = owner

        host.token_encrypted = self.sealer.seal(access_token)
        host.refresh_token_encrypted = (
            self.sealer.seal(refresh_token) if refresh_token else None
        )
        host.expires_at = expires_at
        host.base_url = base_url
        self.db.flush()

        return host

    def remove_host(self, organization_id: str, host_id: str) -> None:
        host = self.host(organization_id, host_id)

        if host is not None:
            self.db.delete(host)
            self.db.flush()

    def remove_oauth_host(
        self, organization_id: str, provider: str, login: str
    ) -> None:
        for host in self.db.scalars(
            select(SourceHost).where(
                SourceHost.organization_id == organization_id,
                SourceHost.kind == provider,
                SourceHost.auth_kind == "oauth",
                SourceHost.login == login,
            )
        ):
            self.db.delete(host)

        self.db.flush()

    def update_host_token(self, organization_id: str, host_id: str, token: str) -> None:
        host = self.host(organization_id, host_id)

        if host is None:
            raise DirectoryError("host not found")

        if not token.strip():
            raise DirectoryError("token is required")

        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        host.token_encrypted = self.sealer.seal(token.strip())
        self.db.flush()

    def set_host_owner(self, organization_id: str, host_id: str, owner: str) -> None:
        host = self.host(organization_id, host_id)

        if host is None:
            raise DirectoryError("host not found")

        host.default_owner = owner.strip() or None
        self.db.flush()
