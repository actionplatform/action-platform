"""Deployment strategies for tests: a target whose operations answer what a test sets, and the checks any target's operations must pass."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

from action_platform.abc.deploy_target import DeployTarget
from action_platform.abc.target_operations import TargetOperations
from action_platform.core.context import Context, DeployResult
from action_platform.core.rollout.operations import (
    OPERATIONS,
    OperationContext,
    OperationResult,
)
from action_platform.core.rollout.strategies import STRATEGIES

ALL = frozenset(OPERATIONS)


class MockOperations(TargetOperations):
    """Every call lands in `calls` as `(operation, params)`; `answers[op]` is the result (or a list consumed in order) an operation returns, ok otherwise."""

    def __init__(
        self,
        supports: Iterable[str] = ALL,
        native: Iterable[str] = (),
        name: str = "mock",
    ) -> None:
        self.name = name
        self.offered = set(supports)
        self.native = set(native)
        self.answers: dict[str, Any] = {}
        self.calls: list[tuple[str, dict]] = []

    def supports(self) -> set[str]:
        return set(self.offered)

    def native_strategies(self) -> set[str]:
        return set(self.native)

    def answer(self, operation: str, *results: OperationResult) -> None:
        self.answers[operation] = list(results)

    def _call(self, operation: str, ctx: OperationContext) -> OperationResult:
        self.calls.append((operation, dict(ctx.params)))

        if operation not in self.offered and operation != "native":
            return self.refuse(operation)

        found = self.answers.get(operation)

        if isinstance(found, list):
            return found.pop(0) if len(found) > 1 else found[0]

        if isinstance(found, OperationResult):
            return found

        return OperationResult(
            True, f"{operation} done", external_ref=f"{operation}-ref"
        )

    def called(self, operation: Optional[str] = None) -> list[str]:
        return [op for op, _ in self.calls if operation is None or op == operation]

    def deploy_new(self, ctx: OperationContext) -> OperationResult:
        return self._call("deploy_new", ctx)

    def shift(self, ctx: OperationContext) -> OperationResult:
        return self._call("shift", ctx)

    def mirror(self, ctx: OperationContext) -> OperationResult:
        return self._call("mirror", ctx)

    def replace(self, ctx: OperationContext) -> OperationResult:
        return self._call("replace", ctx)

    def retire_old(self, ctx: OperationContext) -> OperationResult:
        return self._call("retire_old", ctx)

    def rollback(self, ctx: OperationContext) -> OperationResult:
        return self._call("rollback", ctx)

    def health(self, ctx: OperationContext) -> OperationResult:
        return self._call("health", ctx)

    def status(self, ctx: OperationContext) -> OperationResult:
        return self._call("status", ctx)

    def run_native(
        self, ctx: OperationContext, strategy: str, config: dict
    ) -> OperationResult:
        self.calls.append(("native", {"strategy": strategy, "config": config}))

        if strategy not in self.native:
            return self.refuse(f"run {strategy}")

        found = self.answers.get("native")

        if isinstance(found, list):
            return found.pop(0) if len(found) > 1 else found[0]

        return OperationResult(
            True, "started", external_ref="native-ref", data={"state": "running"}
        )


class MockTarget(DeployTarget):
    """A deploy target for tests: `deploy` notes the version, `operations()` answers `ops` (None keeps it a target that only deploys)."""

    name = "mock"

    def __init__(self, ops: Optional[TargetOperations] = None, **options: Any) -> None:
        self.ops = ops
        self.options = options
        self.deployed: list[str] = []

    def preflight(self, ctx: Context) -> None:
        return None

    def deploy(self, ctx: Context) -> DeployResult:
        self.deployed.append(ctx.next_version)

        return DeployResult(ok=True, target=self.name, version=ctx.next_version)

    def operations(self) -> Optional[TargetOperations]:
        return self.ops


def operation_context(
    root: Path | str = ".", strategy: str = "canary", **fields: Any
) -> OperationContext:
    return OperationContext(
        app=fields.pop("app", "acme/web/demo"),
        tag=fields.pop("tag", "v1.0.0"),
        version=fields.pop("version", "1.0.0"),
        scope=fields.pop("scope", "dev"),
        strategy=strategy,
        deploy=fields.pop("deploy", Context(repo_root=Path(root), stage="dev")),
        **fields,
    )


def contract_problems(ops: TargetOperations, ctx: OperationContext) -> list[str]:
    """What a target's operations break of the contract: unknown ids, unknown native strategies, a call that raises or answers something else than an OperationResult. Empty when it holds."""
    problems: list[str] = []
    offered = set(ops.supports())
    unknown = sorted(offered - ALL)

    if unknown:
        problems.append(f"supports() names unknown operations: {', '.join(unknown)}")

    native = sorted(set(ops.native_strategies()) - set(STRATEGIES))

    if native:
        problems.append(
            f"native_strategies() names unknown strategies: {', '.join(native)}"
        )

    for operation in OPERATIONS:
        try:
            found = getattr(ops, operation)(ctx)
        except Exception as e:
            problems.append(f"{operation} raised {type(e).__name__}: {e}")
            continue

        if not isinstance(found, OperationResult):
            problems.append(
                f"{operation} answered {type(found).__name__}, not an OperationResult"
            )
        elif operation not in offered and found.ok:
            problems.append(f"{operation} is not in supports() but answered ok")

    return problems


__all__ = [
    "ALL",
    "MockOperations",
    "MockTarget",
    "contract_problems",
    "operation_context",
]
