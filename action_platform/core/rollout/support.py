"""Whether a deploy target can run a strategy, and the plan it runs: the target's own when it runs the strategy natively, the core's when it supports every operation the plan needs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from action_platform.core.context import Check
from action_platform.core.exception import DeployError
from action_platform.core.rollout.strategies import (
    STRATEGIES,
    StepSpec,
    native_plan,
    strategy as strategy_of,
    validate_safety,
)

if TYPE_CHECKING:
    from action_platform.abc.deploy_target import DeployTarget
    from action_platform.abc.target_operations import TargetOperations


@dataclass(frozen=True)
class Support:
    strategy: str
    supported: bool
    native: bool = False
    missing: tuple[str, ...] = ()
    reason: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "id": self.strategy,
            "supported": self.supported,
            "native": self.native,
            "missing": list(self.missing),
            "reason": self.reason,
        }


def operations_of(target: "DeployTarget") -> Optional["TargetOperations"]:
    found = getattr(target, "operations", None)

    return found() if callable(found) else None


def support(target: "DeployTarget", strategy: str) -> Support:
    chosen = strategy_of(strategy)
    ops = operations_of(target)
    name = getattr(target, "name", "the target")

    if ops is not None and chosen.id in set(ops.native_strategies()):
        return Support(chosen.id, True, native=True)

    offered = set(ops.supports()) if ops is not None else set()
    missing = tuple(op for op in chosen.needs if op not in offered)

    if not missing:
        return Support(chosen.id, True)

    return Support(
        chosen.id,
        False,
        missing=missing,
        reason=f"{name} cannot run {chosen.id}: it lacks {', '.join(missing)}",
    )


def supports_all(target: "DeployTarget") -> list[Support]:
    return [support(target, id) for id in STRATEGIES]


def plan_for(
    target: "DeployTarget",
    strategy: str,
    config: Optional[dict] = None,
    safety: Optional[dict] = None,
) -> list[StepSpec]:
    chosen = strategy_of(strategy)
    found = support(target, chosen.id)

    if not found.supported:
        raise DeployError(found.reason or f"{chosen.id} is not supported")

    if found.native:
        return native_plan(chosen.id, chosen.validate(config), validate_safety(safety))

    return chosen.plan(config, safety)


def strategy_check(targets: list["DeployTarget"], strategy: str) -> Check:
    chosen = strategy_of(strategy)
    refused = [s for s in (support(t, chosen.id) for t in targets) if not s.supported]

    if not refused:
        return Check("deploy.strategy", True, chosen.id, level="static")

    return Check(
        "deploy.strategy",
        False,
        "; ".join(s.reason or s.strategy for s in refused),
        level="static",
        fix="pick a strategy the target supports, or a target whose plugin offers the missing operations",
    )


__all__ = [
    "Support",
    "operations_of",
    "plan_for",
    "strategy_check",
    "support",
    "supports_all",
]
