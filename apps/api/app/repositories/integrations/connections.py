"""Services an organization connected with OAuth that are not code hosts — one connection per kind, tokens sealed. Refreshing an expiring token is the service's job (`services.integrations.connections`)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.core.db.models import ServiceConnection
from app.core.shared.clock import now
from app.core.shared.ids import new_id
from app.repositories.base import DirectoryBase, DirectoryError


class ConnectionsReads(DirectoryBase):
    def connections_of(self, organization_id: str) -> list[ServiceConnection]:
        return list(
            self.db.scalars(
                select(ServiceConnection)
                .where(ServiceConnection.organization_id == organization_id)
                .order_by(ServiceConnection.kind)
            )
        )

    def connection(
        self, organization_id: str, kind: str
    ) -> Optional[ServiceConnection]:
        return self.db.scalar(
            select(ServiceConnection).where(
                ServiceConnection.organization_id == organization_id,
                ServiceConnection.kind == kind,
            )
        )


class ConnectionsWrites(ConnectionsReads):
    def save_connection(
        self,
        organization_id: str,
        kind: str,
        login: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        scopes: Optional[tuple[str, ...]],
        base_url: Optional[str],
        connected_by: Optional[str] = None,
    ) -> ServiceConnection:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        row = self.connection(organization_id, kind)

        if row is None:
            row = ServiceConnection(
                id=new_id(),
                organization_id=organization_id,
                kind=kind,
                created_at=now(),
            )
            self.db.add(row)

        row.login = login
        row.token_encrypted = self.sealer.seal(access_token)
        row.refresh_token_encrypted = (
            self.sealer.seal(refresh_token) if refresh_token else None
        )
        row.expires_at = expires_at
        row.scopes = " ".join(scopes) if scopes is not None else None
        row.base_url = base_url
        row.connected_by = connected_by
        self.db.flush()

        return row

    def remove_connection(self, organization_id: str, kind: str) -> None:
        row = self.connection(organization_id, kind)

        if row is not None:
            self.db.delete(row)
            self.db.flush()
