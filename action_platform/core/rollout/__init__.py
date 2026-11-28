"""Deployment strategies: the plans the core owns and the operations a deploy target offers to run them."""

from action_platform.core.rollout.operations import (
    OPERATIONS,
    STATES,
    OperationContext,
    OperationResult,
)
from action_platform.core.rollout.strategies import (
    DEFAULT,
    SAFETY_SCHEMA,
    STEP_KINDS,
    STRATEGIES,
    StepSpec,
    Strategy,
    catalog,
    strategy,
    validate_safety,
)
from action_platform.core.rollout.support import (
    Support,
    operations_of,
    plan_for,
    strategy_check,
    support,
    supports_all,
)

__all__ = [
    "DEFAULT",
    "OPERATIONS",
    "OperationContext",
    "OperationResult",
    "SAFETY_SCHEMA",
    "STATES",
    "STEP_KINDS",
    "STRATEGIES",
    "StepSpec",
    "Strategy",
    "Support",
    "catalog",
    "operations_of",
    "plan_for",
    "strategy",
    "strategy_check",
    "support",
    "supports_all",
    "validate_safety",
]
