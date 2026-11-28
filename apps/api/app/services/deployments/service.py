"""App › Deployments: ship a release to the app's deploy target and read what is live — the core's deployer on the app's clone, with the identity and the environment the platform signs and fills."""

from dataclasses import asdict
from typing import Callable, Optional

from sqlalchemy import select

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ActionPlatformError, DeployError
from action_platform.core.facade import ActionPlatform
from action_platform.core.rollout import (
    STRATEGIES,
    OperationContext,
    OperationResult,
    StepSpec,
    strategy as strategy_of,
    strategy_check,
    supports_all,
)
from app.core.db.models import App
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.scopes import ScopeStore
from app.repositories.workspace.registry import Registry
from app.schemas import DeployRequest, SourceCredentials
from app.services.deployments.rollout import StepCall, perform, plan_of
from app.services.integrations.plugins.connections import ConnectionGuard
from app.services.scopes import ScopesService
from app.services.workspace import Workspaces
from app.services.workspace import git_auth as auth


class DeploymentsService:
    def __init__(
        self,
        registry: Registry,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
        configs: ConfigStore | None = None,
        credentials: SourceCredentials | None = None,
        ci: list[CIRunner] | None = None,
        guard: ConnectionGuard | None = None,
    ) -> None:
        self.registry = registry
        self.ci = list(ci or [])
        self.identity = identity
        self.env = env
        self.guard = guard or ConnectionGuard(env or {}, False)
        self.configs = configs or ConfigStore(registry.store.database)
        self.credentials = credentials

    def _scopes(self, id: str) -> list[dict]:
        """The app's scopes as the platform keeps them, in place of whatever platform.toml says; an app the platform does not know keeps the file's."""
        with self.registry.store.database.session() as db:
            app = db.scalar(select(App).where(App.registry_id == id))

            if app is None:
                return []

            return [
                ScopeStore.as_toml(spec)
                for spec in ScopesService(db, self.configs).specs(app)
            ]

    def _tool(self, id: str) -> ActionPlatform:
        _, root = Workspaces(self.registry).checkout(id)
        config = auth.apply(self.configs.config(id, root), self.credentials)
        config.ci = [*config.ci, *self.ci]
        config._scopes_spec = self._scopes(id)
        self.guard.check(config.targets)

        return ActionPlatform(
            config=config,
            repo_root=root,
            identity=self.identity,
            env=self.env,
        )

    def deploy(self, id: str, body: DeployRequest) -> list[dict]:
        tool = self._tool(id)

        if body.strategy:
            found = strategy_check(
                tool.deployer.targets(None, body.scope or body.stage), body.strategy
            )

            if not found.ok:
                raise DeployError(found.detail)

        results = tool.deploy(
            stage=body.scope or body.stage, dry_run=body.dry_run, version=body.version
        )

        return [
            {
                "target": r.target,
                "ok": r.ok,
                "version": r.version,
                "url": r.url,
                "error": r.error,
                "stage": r.stage,
            }
            for r in results
        ]

    def plans(
        self, id: str, body: DeployRequest
    ) -> list[tuple[str, list[StepSpec], list[str]]]:
        """Per target the deploy runs on the scope: the steps of the chosen strategy and the operations the target offers; refused when one target cannot run it."""
        strategy = strategy_of(body.strategy).id
        tool = self._tool(id)

        return [
            (target.name, *plan_of(target, strategy, body.strategy_config, body.safety))
            for target in tool.deployer.targets(None, body.scope or body.stage)
        ]

    def strategies(self, id: str, stage: str) -> list[dict]:
        """Per strategy, whether every target the platform runs on `stage` can run it — natively or with the operations it offers — and why not."""
        config = auth.apply(self.configs.config_of(id), self.credentials)
        config.ci = [*config.ci, *self.ci]

        try:
            self.guard.check(config.targets)
            targets = config.runnable(None, stage)
        except ActionPlatformError as e:
            return [
                {
                    "id": name,
                    "supported": False,
                    "native": False,
                    "missing": [],
                    "reason": str(e),
                }
                for name in STRATEGIES
            ]

        found: dict[str, dict] = {}

        for target in targets:
            for support in supports_all(target):
                row = found.setdefault(
                    support.strategy,
                    {
                        "id": support.strategy,
                        "supported": True,
                        "native": True,
                        "missing": [],
                        "reasons": [],
                    },
                )
                row["supported"] = row["supported"] and support.supported
                row["native"] = row["native"] and support.native
                row["missing"] += [
                    m for m in support.missing if m not in row["missing"]
                ]

                if support.reason:
                    row["reasons"].append(support.reason)

        if not targets:
            return [
                {
                    "id": name,
                    "supported": False,
                    "native": False,
                    "missing": [],
                    "reason": f"no target the platform runs serves {stage}",
                }
                for name in STRATEGIES
            ]

        return [
            {
                "id": row["id"],
                "supported": row["supported"],
                "native": row["native"],
                "missing": row["missing"],
                "reason": "; ".join(row["reasons"]) or None,
            }
            for row in found.values()
        ]

    def run_step(self, id: str, call: StepCall) -> OperationResult:
        """One operation of one deployment step, on the clone at the release tag, with the context a deploy gets."""
        tool = self._tool(id)
        deployer = tool.deployer
        tag, shipped = deployer.release_tag(call.version)
        ctx = deployer._context(stage=call.stage)
        ctx.criticality = tool.config.scope(ctx.stage).criticality
        ctx.current_version = ctx.next_version = shipped
        ctx.tag = tag

        with deployer.at_release(tag):
            target = next(iter(deployer.runnable(call.target, call.stage)), None)

            if target is None:
                return OperationResult(
                    False, f"no deploy target {call.target} serves {call.stage}"
                )

            return perform(
                tool,
                target,
                call,
                OperationContext(
                    app=str(ctx.env.get("AP_APP") or ""),
                    tag=tag,
                    version=shipped,
                    scope=call.stage,
                    strategy=call.strategy,
                    deploy=ctx,
                    config=call.config,
                    params=call.params,
                    operation=call.operation,
                    deployment_id=call.deployment_id,
                    step=call.position,
                    external_ref=call.external_ref,
                    data=call.data,
                ),
            )

    def release_of(self, id: str, version: Optional[str]) -> Optional[str]:
        """The version a deploy will ship: the one named, else the release the clone's HEAD sits on; None when there is none to ship."""
        try:
            return self._tool(id).deployer.release_tag(version)[1]
        except ActionPlatformError:
            return version

    def destroy(self, id: str, stages: tuple[str, ...] | None = None) -> None:
        """Every scope's stack down — the app's scopes unless `stages` names them."""
        tool = self._tool(id)

        for stage in stages or tuple(s["name"] for s in self._scopes(id)):
            tool.destroy(stage=stage)

    def diagnose(self, id: str, stage: Optional[str]) -> list[dict]:
        return [asdict(r) for r in self._tool(id).diagnose(stage=stage)]
