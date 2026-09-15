"""External provider discovery via entry_points."""

from __future__ import annotations

from importlib.metadata import entry_points

from action_platform.plugins import registry


def load_providers(group: str) -> dict[str, type]:
    """Every entry point of `group`, minus those shipped by a plugin the user disabled."""
    off = registry.installed().disabled_packages()

    return {
        ep.name: ep.load()
        for ep in entry_points(group=group)
        if (getattr(getattr(ep, "dist", None), "name", "") or "") not in off
    }


def load_source_hosts() -> dict[str, type]:
    return load_providers("action_platform.source_host")


def load_ci_runners() -> dict[str, type]:
    return load_providers("action_platform.ci_runner")


def load_deploy_targets() -> dict[str, type]:
    return load_providers("action_platform.deploy_target")


def load_release_strategies() -> dict[str, type]:
    return load_providers("action_platform.release_strategy")


def load_changelog_renderers() -> dict[str, type]:
    return load_providers("action_platform.changelog")
