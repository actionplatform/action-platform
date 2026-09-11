"""Devtool settings module."""

import os
from pathlib import Path


class Settings:
    CONFIG_FILE = "devtool.toml"
    LAST_VERSION_FILE = "LAST_VERSION"
    HOOKS_DIR = Path(".devtool/hooks")
    CHANGELOG_FILE = "CHANGELOG.md"

    GITHUB_TOKEN = os.getenv("DEVTOOL_GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    GITLAB_TOKEN = os.getenv("DEVTOOL_GITLAB_TOKEN") or os.getenv("GITLAB_TOKEN")
    JENKINS_USER = os.getenv("DEVTOOL_JENKINS_USER")
    JENKINS_TOKEN = os.getenv("DEVTOOL_JENKINS_TOKEN")
    DOKPLOY_TOKEN = os.getenv("DEVTOOL_DOKPLOY_TOKEN")
    SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")


settings = Settings()
