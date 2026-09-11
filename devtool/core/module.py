"""External provider discovery via entry_points."""

from __future__ import annotations

from importlib.metadata import entry_points


def load_providers(group: str) -> dict[str, type]:
    return {ep.name: ep.load() for ep in entry_points(group=group)}


def load_source_hosts() -> dict[str, type]:
    return load_providers("devtool.source_host")


def load_ci_runners() -> dict[str, type]:
    return load_providers("devtool.ci_runner")


def load_deploy_targets() -> dict[str, type]:
    return load_providers("devtool.deploy_target")
