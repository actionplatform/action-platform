"""App › Deployments: ship a release to the app's deploy target and read what is live — the core's deployer on the app's clone, with the identity and the environment the platform signs and fills."""

from dataclasses import asdict
from typing import Callable, Optional

from action_platform.core.action_platform import ActionPlatform
from app.repositories.config_store import ConfigStore
from app.repositories.registry import Registry
from app.schemas import DeployRequest
from app.services.workspace import Workspaces


class DeploymentsService:
    def __init__(
        self,
        registry: Registry,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        configs: ConfigStore | None = None,
    ) -> None:
        self.registry = registry
        self.identity = identity
        self.env = env
        self.configs = configs or ConfigStore(registry.store.database)

    def _tool(self, id: str) -> ActionPlatform:
        _, root = Workspaces(self.registry).checkout(id)

        return ActionPlatform(
            config=self.configs.config(id, root),
            repo_root=root,
            identity=self.identity,
            env=self.env,
        )

    def deploy(self, id: str, body: DeployRequest) -> list[dict]:
        results = self._tool(id).deploy(
            stage=body.stage, dry_run=body.dry_run, version=body.version
        )

        return [
            {
                "target": r.target,
                "ok": r.ok,
                "version": r.version,
                "url": r.url,
                "error": r.error,
            }
            for r in results
        ]

    def diagnose(self, id: str, stage: Optional[str]) -> list[dict]:
        return [asdict(r) for r in self._tool(id).diagnose(stage=stage)]
