"""How every entry point starts — the CLI, the MCP server and the API run the same sequence: `.env`, then observability; and how they open a project on disk."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from action_platform.core.config import Config
from action_platform.core.facade import ActionPlatform
from action_platform.core.files import CONFIG_FILE
from action_platform.env import load
from action_platform.observability import observe
from action_platform.settings import Settings, settings


def bootstrap(
    component: str,
    version: Optional[str] = None,
    env_file: Optional[Path] = None,
) -> Settings:
    """Load `env_file` (default: `.env` in the working directory) for what the shell did not set, start Sentry as `component`, and hand back the settings read from that environment."""
    load(env_file)
    observe(component, settings.observability, version=version)

    return settings


def project(root: Optional[Path] = None) -> ActionPlatform:
    """The facade for the project at `root` (default: the working directory), configured from its platform.toml."""
    root = root or Path.cwd()

    return ActionPlatform(config=Config.from_toml(root / CONFIG_FILE), repo_root=root)
