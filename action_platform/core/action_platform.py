"""DevTool orchestrator."""

from __future__ import annotations

from pathlib import Path

from devtool.core import pipeline
from devtool.core.config import Config
from devtool.core.context import Context, DeployResult


class DevTool:
    """
    Import:
        from devtool import DevTool, Config

    Example:
        tool = DevTool(config=Config(...))
        tool.release("patch")
        tool.deploy(target="dokploy")

    Args:
        config (Config): configuration with injected providers.
        repo_root (Path): repository root. Defaults to cwd.

    Attributes:
        config (Config):
        repo_root (Path):
    """

    def __init__(self, config: Config | None = None, repo_root: Path | None = None) -> None:
        self.config = config or Config()
        self.repo_root = repo_root or Path.cwd()

    def release(self, level: str = "patch", dry_run: bool = False) -> Context:
        return pipeline.release(self.config, level, self.repo_root, dry_run=dry_run)

    def deploy(self, target: str | None = None, dry_run: bool = False) -> list[DeployResult]:
        return pipeline.deploy(self.config, target, self.repo_root, dry_run=dry_run)
