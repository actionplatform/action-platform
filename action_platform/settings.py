"""Action Platform settings module."""

import os
from pathlib import Path


class Settings:
    CONFIG_FILE = "platform.toml"
    LAST_VERSION_FILE = "LAST_VERSION"
    HOOKS_DIR = Path(".action-platform/hooks")
    CHANGELOG_FILE = "CHANGELOG.md"

    TEMPLATES_REPO = os.getenv(
        "ACTION_PLATFORM_TEMPLATES_REPO",
        "https://github.com/actionplatform/templates.git",
    )
    TEMPLATES_DIR = os.getenv("ACTION_PLATFORM_TEMPLATES")
    TEMPLATES_CACHE = Path.home() / ".cache" / "action-platform" / "templates"

    GITHUB_TOKEN = os.getenv("ACTION_PLATFORM_GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    GITLAB_TOKEN = os.getenv("ACTION_PLATFORM_GITLAB_TOKEN") or os.getenv(
        "GITLAB_TOKEN"
    )
    SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")


settings = Settings()
