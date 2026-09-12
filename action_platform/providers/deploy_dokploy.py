"""Dokploy DeployTarget provider."""

from __future__ import annotations

from devtool.abc.deploy_target import DeployTarget
from devtool.core.context import Context, DeployResult


class DeployDokploy(DeployTarget):
    """
    Import:
        from devtool.providers import DeployDokploy

    Example:
        DeployDokploy(url="https://dokploy.internal", app="my-project-prod")

    Args:
        url (str): Dokploy base URL.
        app (str): application ID/slug.
        token (str): overrides DEVTOOL_DOKPLOY_TOKEN env var.
    """

    name = "dokploy"

    def __init__(self, url: str, app: str, token: str | None = None) -> None:
        self.url = url.rstrip("/")
        self.app = app
        self.token = token

    def preflight(self, ctx: Context) -> None:
        raise NotImplementedError

    def deploy(self, ctx: Context) -> DeployResult:
        raise NotImplementedError

    def rollback(self, ctx: Context, to_version: str) -> None:
        raise NotImplementedError
