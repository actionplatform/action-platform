"""TargetOperations ABC — the small steps a deploy target offers so the platform can run a strategy on it.

A target returns one from `DeployTarget.operations()`. `supports()` names the operations it implements, `native_strategies()` the strategies it runs itself. Every call answers an OperationResult; an operation the target cannot do answers `ok=False`, never raises."""

from __future__ import annotations

from abc import ABC

from action_platform.core.rollout.operations import OperationContext, OperationResult


class TargetOperations(ABC):
    """TargetOperations"""

    name: str = ""

    def supports(self) -> set[str]:
        return set()

    def native_strategies(self) -> set[str]:
        return set()

    def deploy_new(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("deploy_new")

    def shift(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("shift")

    def mirror(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("mirror")

    def replace(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("replace")

    def retire_old(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("retire_old")

    def rollback(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("rollback")

    def health(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("health")

    def status(self, ctx: OperationContext) -> OperationResult:
        return self.refuse("status")

    def run_native(
        self, ctx: OperationContext, strategy: str, config: dict
    ) -> OperationResult:
        return self.refuse(f"run {strategy}")

    def refuse(self, operation: str) -> OperationResult:
        return OperationResult(False, f"{self.name or 'the target'} cannot {operation}")
