"""What connecting a provider asks for: the platform's own scopes and permissions, then what the enabled plugins declare in `connections`."""

from action_platform.plugins import registry
from action_platform.plugins.registry import PERMISSION_RANK


def scopes_for(kind: str, own: str) -> str:
    asked = own.split()

    for scope in registry.installed().connection_scopes(kind):
        if scope not in asked:
            asked.append(scope)

    return " ".join(asked)


def permissions_for(kind: str, own: dict[str, str]) -> dict[str, str]:
    merged = dict(own)

    for name, level in registry.installed().connection_permissions(kind).items():
        if PERMISSION_RANK.get(level, 0) > PERMISSION_RANK.get(merged.get(name, ""), 0):
            merged[name] = level

    return merged


__all__ = ["PERMISSION_RANK", "permissions_for", "scopes_for"]
