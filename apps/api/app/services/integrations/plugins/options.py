"""The plugin options store backed by the database — what the file backend is on a machine. Rows belong to an organization; the empty organization holds the platform-wide defaults an organization's own values override.

A plugin reads the organization's connections through `credential(kind)` — the code host it connected (GitHub, GitLab, Bitbucket) or a service connected under Settings (Sentry) — only for a kind it declares in `connections`; the token is refreshed when it is about to expire and handed to that call alone.

An option the plugin declares with kind `secret` is sealed at rest (`{"$sealed": "<AES-256-GCM>"}`, the same Sealer as the code hosts' tokens) and is never handed back to a browser: `public()` leaves it out and `stored_secrets()` only says it is set. It is opened for the process that needs it — a deploy job's environment."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import Credential, Options, registry
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import PluginOption
from app.repositories.base import HOST_KINDS
from app.services.integrations.connections.credentials import FreshConnections
from app.services.integrations.hosts.credentials import FreshCredentials

PLATFORM = ""
SEALED = "$sealed"


def secret_keys(slug: str) -> set[str]:
    """The keys the plugin declares as `secret`."""
    for row in registry.installed().rows():
        if row["slug"] == slug:
            return {o["key"] for o in row["options"] if o.get("kind") == "secret"}

    return set()


def is_sealed(raw: str) -> bool:
    value = json.loads(raw)

    return isinstance(value, dict) and set(value) == {SEALED}


def encode(value: Any, secret: bool, sealer: Optional[Sealer]) -> str:
    if not secret:
        return json.dumps(value)

    if sealer is None:
        raise ActionPlatformError(
            "AP_AUTH_SECRET is not set: nothing to seal a plugin secret with"
        )

    return json.dumps({SEALED: sealer.seal(json.dumps(value))})


def decode(raw: str, sealer: Optional[Sealer]) -> Any:
    value = json.loads(raw)

    if not (isinstance(value, dict) and set(value) == {SEALED}):
        return value

    if sealer is None:
        raise ActionPlatformError(
            "AP_AUTH_SECRET is not set: a sealed plugin secret cannot be opened"
        )

    return json.loads(sealer.open(value[SEALED]))


def reseal(database: Database, sealer: Optional[Sealer]) -> int:
    """Seal every secret still stored in plain text — the rows written before secrets were sealed. Returns how many."""
    if sealer is None:
        return 0

    sealed = 0

    with database.session() as s:
        for row in s.scalars(select(PluginOption)).all():
            if row.key in secret_keys(row.plugin) and not is_sealed(row.value):
                row.value = encode(json.loads(row.value), True, sealer)
                sealed += 1

        s.commit()

    return sealed


def merge(rows: list[PluginOption], organization_id: str) -> dict[str, str]:
    """Raw values, the organization's over the platform's defaults."""
    merged = {r.key: r.value for r in rows if r.organization_id == PLATFORM}
    merged.update(
        {r.key: r.value for r in rows if r.organization_id == organization_id}
    )

    return merged


def opened(
    db: DbSession, slug: str, organization_id: str, sealer: Optional[Sealer]
) -> dict[str, Any]:
    """The organization's values of the plugin over the platform's defaults, secrets opened, read through a session already open."""
    rows = list(
        db.scalars(
            select(PluginOption).where(
                PluginOption.plugin == slug,
                PluginOption.organization_id.in_({PLATFORM, organization_id}),
            )
        ).all()
    )

    return {
        key: decode(raw, sealer) for key, raw in merge(rows, organization_id).items()
    }


class ReadOptions(Options):
    """A plugin's options as they were read, for a call that only reads them."""

    def __init__(self, slug: str, values: dict[str, Any]) -> None:
        self.slug = slug
        self.values = dict(values)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        raise ActionPlatformError(f"plugin {self.slug}: options are read-only here")

    def delete(self, key: str) -> None:
        raise ActionPlatformError(f"plugin {self.slug}: options are read-only here")

    def all(self) -> dict[str, Any]:
        return dict(self.values)


class DbOptions(Options):
    def __init__(
        self,
        database: Database,
        slug: str,
        organization_id: str = PLATFORM,
        sealer: Optional[Sealer] = None,
    ) -> None:
        self.database = database
        self.slug = slug
        self.organization_id = organization_id or PLATFORM
        self.sealer = sealer

    def _key(self, key: str, organization_id: str) -> tuple[str, str, str]:
        return (organization_id, self.slug, key)

    def get(self, key: str, default: Any = None) -> Any:
        with self.database.session() as s:
            row = s.get(PluginOption, self._key(key, self.organization_id))

            if row is None and self.organization_id != PLATFORM:
                row = s.get(PluginOption, self._key(key, PLATFORM))

            return decode(row.value, self.sealer) if row else default

    def set(self, key: str, value: Any) -> None:
        raw = encode(value, key in secret_keys(self.slug), self.sealer)

        with self.database.session() as s:
            row = s.get(PluginOption, self._key(key, self.organization_id))

            if row is None:
                row = PluginOption(
                    organization_id=self.organization_id, plugin=self.slug, key=key
                )
                s.add(row)

            row.value = raw
            s.commit()

    def delete(self, key: str) -> None:
        with self.database.session() as s:
            s.execute(
                delete(PluginOption).where(
                    PluginOption.organization_id == self.organization_id,
                    PluginOption.plugin == self.slug,
                    PluginOption.key == key,
                )
            )
            s.commit()

    def credential(self, kind: str) -> Optional[Credential]:
        if self.organization_id == PLATFORM or not registry.installed().declares(
            self.slug, kind
        ):
            return None

        with self.database.session() as s:
            found = (
                self._host_credential(s, kind)
                if kind in HOST_KINDS
                else FreshConnections(s, self.sealer).credential(
                    self.organization_id, kind
                )
            )
            s.commit()

        return found

    def _host_credential(self, s: Any, kind: str) -> Optional[Credential]:
        reads = FreshCredentials(s, self.sealer)
        hosts = sorted(
            (h for h in reads.hosts_of(self.organization_id) if h.kind == kind),
            key=lambda h: h.auth_kind != "oauth",
        )

        if not hosts:
            return None

        host = hosts[0]
        creds = reads.credentials_for(self.organization_id, host.id)

        if creds is None:
            return None

        app = reads.oauth_app(kind) if host.auth_kind == "oauth" else None

        return Credential(
            kind=kind,
            token=creds.token,
            login=host.login or host.username or "",
            api_url=host.base_url,
            app=app.slug if app else None,
        )

    def _rows(self) -> list[PluginOption]:
        with self.database.session() as s:
            return list(
                s.scalars(
                    select(PluginOption).where(
                        PluginOption.plugin == self.slug,
                        PluginOption.organization_id.in_(
                            {PLATFORM, self.organization_id}
                        ),
                    )
                ).all()
            )

    def _merged(self) -> dict[str, str]:
        return merge(self._rows(), self.organization_id)

    def all(self) -> dict[str, Any]:
        """The organization's values over the platform's defaults, secrets opened — for the processes that use them, never for a response."""
        return {key: decode(raw, self.sealer) for key, raw in self._merged().items()}

    def public(self) -> dict[str, Any]:
        """What a browser may see: every value but the secrets."""
        secrets = secret_keys(self.slug)

        return {
            key: json.loads(raw)
            for key, raw in self._merged().items()
            if key not in secrets
        }

    def stored_secrets(self) -> list[str]:
        """The secret keys that hold a value, without the value."""
        secrets = secret_keys(self.slug)

        return sorted(key for key in self._merged() if key in secrets)
