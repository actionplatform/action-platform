"""The plugin options store backed by the database — what the file backend is on a machine. Rows belong to an organization; the empty organization holds the platform-wide defaults an organization's own values override.

An option the plugin declares with kind `secret` is sealed at rest (`{"$sealed": "<AES-256-GCM>"}`, the same Sealer as the code hosts' tokens) and is never handed back to a browser: `public()` leaves it out and `stored_secrets()` only says it is set. It is opened for the process that needs it — a deploy job's environment."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import delete, select

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import Options, registry
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import PluginOption

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
        """Raw values, the organization's over the platform's defaults."""
        rows = self._rows()
        merged = {r.key: r.value for r in rows if r.organization_id == PLATFORM}
        merged.update(
            {r.key: r.value for r in rows if r.organization_id == self.organization_id}
        )

        return merged

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
