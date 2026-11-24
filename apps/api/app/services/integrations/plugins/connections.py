"""A plugin's connection is one record: the options of one owner, the organization's own or — only for the organizations `AP_PLATFORM_CONNECTIONS` names — the platform's. A deploy target never takes an endpoint from `platform.toml` that differs from the connection it would send the credential to, and never falls back to the platform's environment the policy does not grant."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ConfigError
from action_platform.core.targets import TargetSpec
from action_platform.plugins import registry
from action_platform.settings import settings
from app.core.db.models import Organization, PluginOption

PLATFORM = ""
EVERY = "*"
DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class SharedConnections:
    allowed: tuple[str, ...] = ()

    @classmethod
    def from_settings(cls) -> "SharedConnections":
        return cls(settings.api.platform_connections)

    def allows(self, organization: Optional[Organization]) -> bool:
        if organization is None:
            return False

        return EVERY in self.allowed or (organization.slug or "").lower() in {
            s.lower() for s in self.allowed
        }


def owner_of(
    db: DbSession,
    slug: str,
    organization_id: str,
    policy: Optional[SharedConnections] = None,
) -> Optional[str]:
    """Whose options make the plugin's connection for `organization_id`: its own when it keeps any, the platform's when the policy grants it, else nobody."""
    if organization_id == PLATFORM:
        return PLATFORM

    own = db.scalar(
        select(PluginOption.key)
        .where(
            PluginOption.organization_id == organization_id,
            PluginOption.plugin == slug,
        )
        .limit(1)
    )

    if own is not None:
        return organization_id

    policy = policy or SharedConnections.from_settings()

    return PLATFORM if policy.allows(db.get(Organization, organization_id)) else None


def env_prefix(name: str) -> str:
    return "AP_" + re.sub(r"[^A-Za-z0-9]", "_", name).upper() + "_"


def env_name(slug: str, key: str) -> str:
    return env_prefix(slug) + re.sub(r"[^A-Za-z0-9]", "_", key).upper()


def endpoint(url: str) -> tuple[str, str, int, str]:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()

    try:
        port = parts.port or DEFAULT_PORTS.get(scheme, 0)
    except ValueError:
        port = -1

    return (scheme, (parts.hostname or "").lower(), port, parts.path.rstrip("/"))


@dataclass(frozen=True)
class ConnectionGuard:
    env: Mapping[str, str] = field(default_factory=dict)
    shared: bool = False
    ambient: Mapping[str, str] = field(default_factory=lambda: os.environ)

    def check(self, targets: Iterable[TargetSpec]) -> None:
        """Raise ConfigError for the first target whose endpoint or credential would not come from the app's one connection."""
        for spec in targets:
            plugin = self._plugin(spec.kind)

            if plugin is not None:
                self._check(spec, plugin)

    @staticmethod
    def _plugin(kind: str):
        prefix = env_prefix(kind)

        for row in registry.installed().enabled():
            if env_prefix(row.slug) == prefix:
                return row.plugin

        return None

    def _check(self, spec: TargetSpec, plugin) -> None:
        urls = [o.key for o in plugin.options if o.kind == "url"]
        secrets = [o.key for o in plugin.options if o.kind == "secret"]
        keys = urls + secrets
        names = {k: env_name(plugin.slug, k) for k in keys}
        written = {k for k in keys if spec.options.get(k)}
        connection = {k: self.env[names[k]] for k in keys if self.env.get(names[k])}

        if not connection and self.shared:
            connection = {
                k: self.ambient[names[k]] for k in keys if self.ambient.get(names[k])
            }

        for key in urls:
            if key not in written:
                continue

            stored = connection.get(key)

            if stored is not None and endpoint(str(spec.options[key])) != endpoint(
                stored
            ):
                raise ConfigError(
                    f"{spec.name}: platform.toml points {key} at a different host than the organization's {plugin.slug} connection; "
                    f"remove {key} from the target or make it match the connection"
                )

            if stored is None and any(
                k in connection and k not in written for k in secrets
            ):
                raise ConfigError(
                    f"{spec.name}: platform.toml sets {key} but the organization's {plugin.slug} connection has no {key} to check it against; "
                    f"set {key} on the connection under Settings › Plugins or remove it from the target"
                )

        borrowed = [
            names[k]
            for k in keys
            if k not in written and k not in connection and self.ambient.get(names[k])
        ]

        if borrowed:
            raise ConfigError(
                f"{spec.name}: {', '.join(borrowed)} would come from the platform's environment, "
                f"not from the {plugin.slug} connection this organization may use; "
                f"connect {plugin.slug} under Settings › Plugins or grant it with AP_PLATFORM_CONNECTIONS"
            )
