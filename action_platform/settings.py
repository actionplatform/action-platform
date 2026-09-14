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
    ALLOW_UNAUTHENTICATED_API = os.getenv("AP_ALLOW_UNAUTHENTICATED", "") == "1"
    FORWARDED_ALLOW_IPS = os.getenv("AP_FORWARDED_ALLOW_IPS", "*")
    DATABASE_URL = os.getenv("AP_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    DATABASE_POOL_SIZE = int(os.getenv("AP_DATABASE_POOL_SIZE", "5"))
    AUTH_SECRET = os.getenv("AP_AUTH_SECRET") or os.getenv("BETTER_AUTH_SECRET", "")
    PUBLIC_URL = os.getenv("AP_PUBLIC_URL") or os.getenv("PUBLIC_URL", "")
    SENTRY_DSN = os.getenv("AP_SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.getenv("AP_SENTRY_ENVIRONMENT", "production")
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("AP_SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    GIT_AUTHOR_NAME = os.getenv("AP_GIT_AUTHOR_NAME", "Action Platform")
    GIT_AUTHOR_EMAIL = os.getenv("AP_GIT_AUTHOR_EMAIL", "cloud@actionplatform.io")
    GITLAB_TOKEN = os.getenv("ACTION_PLATFORM_GITLAB_TOKEN") or os.getenv(
        "GITLAB_TOKEN"
    )
    BITBUCKET_TOKEN = os.getenv("ACTION_PLATFORM_BITBUCKET_TOKEN")
    BITBUCKET_USERNAME = os.getenv("ACTION_PLATFORM_BITBUCKET_USERNAME")

    @staticmethod
    def env(name: str) -> str:
        return os.getenv(name, "")


settings = Settings()
