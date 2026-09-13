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

    ALLOW_FILE_URLS = os.getenv("AP_ALLOW_FILE_URLS") == "1"
    ALLOW_INSECURE_HTTP = os.getenv("AP_ALLOW_INSECURE_HTTP") == "1"
    GIT_HOSTS = [
        h.strip().lower()
        for h in os.getenv("ACTION_PLATFORM_GIT_HOSTS", "").split(",")
        if h.strip()
    ]

    GITHUB_TOKEN = os.getenv("ACTION_PLATFORM_GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    API_TOKEN = os.getenv("AP_API_TOKEN", "")
    GITLAB_TOKEN = os.getenv("ACTION_PLATFORM_GITLAB_TOKEN") or os.getenv(
        "GITLAB_TOKEN"
    )
    BITBUCKET_TOKEN = os.getenv("ACTION_PLATFORM_BITBUCKET_TOKEN")
    BITBUCKET_USERNAME = os.getenv("ACTION_PLATFORM_BITBUCKET_USERNAME")


settings = Settings()
