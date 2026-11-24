"""Who a generated project belongs to: the account that owns its repository, the name it is authored under, its licence and host."""

from __future__ import annotations

import os
import shutil
import subprocess

from action_platform.core.exception import ProviderError, TemplateError
from action_platform.options import SourceTokens
from action_platform.providers.source import rest

LICENSES = ("none", "mit", "apache-2.0")
HOSTS = ("github", "gitlab", "bitbucket")


def host_for(ci: str | None) -> str:
    """The code host a CI implies: GitLab for GitLab CI, Bitbucket for Pipelines, GitHub otherwise."""
    return ci if ci in ("gitlab", "bitbucket") else "github"


def check(license_: str, host: str) -> None:
    if license_ not in LICENSES:
        raise TemplateError(
            f"unknown license: {license_} (available: {', '.join(LICENSES)})"
        )

    if host not in HOSTS:
        raise TemplateError(f"unknown host: {host} (available: {', '.join(HOSTS)})")


def account(kind: str, tokens: SourceTokens | None = None) -> str:
    """The login this machine's credentials for `kind` belong to — the host token, else the gh CLI for GitHub, else the Bitbucket username; empty when none answers."""
    tokens = SourceTokens.from_env(os.environ) if tokens is None else tokens
    token = tokens.token(kind)

    try:
        if kind == "github" and token:
            return str(
                rest.call(
                    "GET",
                    "https://api.github.com/user",
                    {"authorization": f"Bearer {token}"},
                ).get("login")
                or ""
            )

        if kind == "github" and shutil.which("gh"):
            found = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return found.stdout.strip() if found.returncode == 0 else ""

        if kind == "gitlab" and token:
            return str(
                rest.call(
                    "GET",
                    "https://gitlab.com/api/v4/user",
                    {"authorization": f"Bearer {token}"},
                ).get("username")
                or ""
            )
    except (ProviderError, OSError, subprocess.SubprocessError, AttributeError):
        return ""

    if kind == "bitbucket":
        return tokens.username(kind) or ""

    return ""


def git_author() -> str:
    """`git config user.name`; empty when git has none."""
    try:
        found = subprocess.run(
            ["git", "config", "user.name"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    return found.stdout.strip() if found.returncode == 0 else ""
