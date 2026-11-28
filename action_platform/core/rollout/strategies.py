"""The deployment strategies the core owns: stable ids, a config schema each, the operations its plan needs, and the plan itself — the steps a deployment runs, built once when it starts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from action_platform.core.exception import ConfigError

STEP_KINDS = (
    "deploy_new",
    "shift",
    "mirror",
    "replace",
    "retire_old",
    "rollback",
    "health",
    "pause",
    "approval",
    "native",
)
TRAFFIC = ("shift", "replace", "mirror")


@dataclass(frozen=True)
class StepSpec:
    kind: str
    params: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "params": dict(self.params)}


def integer(default: int, minimum: int, maximum: Optional[int] = None) -> dict:
    found: dict[str, Any] = {"type": "integer", "minimum": minimum, "default": default}

    if maximum is not None:
        found["maximum"] = maximum

    return found


def schema(properties: dict[str, dict]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }


CANARY_STEPS = [
    {"weight": 5, "pause_seconds": 300},
    {"weight": 25, "pause_seconds": 300},
    {"weight": 50, "pause_seconds": 300},
    {"weight": 100, "pause_seconds": 0},
]

SAFETY_SCHEMA = schema(
    {
        "auto_rollback": {"type": "boolean", "default": True},
        "manual_approval": {"type": "boolean", "default": False},
        "bake_seconds": integer(0, 0),
    }
)


def normalize(spec: dict, value: Any, where: str) -> Any:
    """`value` checked against the schema subset the strategies use, defaults filled in."""
    kind = spec.get("type")

    if value is None and "default" in spec:
        value = _copy(spec["default"])

    if kind == "object":
        value = {} if value is None else value

        if not isinstance(value, dict):
            raise ConfigError(f"{where} must be an object")

        properties = spec.get("properties", {})
        unknown = sorted(set(value) - set(properties))

        if unknown and spec.get("additionalProperties") is False:
            raise ConfigError(f"{where} has unknown keys: {', '.join(unknown)}")

        missing = [k for k in spec.get("required", []) if k not in value]

        if missing:
            raise ConfigError(f"{where} needs {', '.join(missing)}")

        return {
            k: normalize(s, value.get(k), f"{where}.{k}")
            for k, s in properties.items()
            if k in value or "default" in s
        }

    if kind == "array":
        if not isinstance(value, list):
            raise ConfigError(f"{where} must be a list")

        if len(value) < spec.get("minItems", 0):
            raise ConfigError(f"{where} needs at least {spec['minItems']} item(s)")

        return [
            normalize(spec["items"], item, f"{where}[{i}]")
            for i, item in enumerate(value)
        ]

    if kind == "boolean":
        if not isinstance(value, bool):
            raise ConfigError(f"{where} must be true or false")

        return value

    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{where} must be a whole number")

        if value < spec.get("minimum", value):
            raise ConfigError(f"{where} must be at least {spec['minimum']}")

        if value > spec.get("maximum", value):
            raise ConfigError(f"{where} must be at most {spec['maximum']}")

        return value

    return value


def _copy(value: Any) -> Any:
    if isinstance(value, list):
        return [_copy(v) for v in value]

    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}

    return value


@dataclass(frozen=True)
class Strategy:
    id: str
    label: str
    description: str
    config_schema: dict
    needs: tuple[str, ...]
    steps: Callable[[dict], list[StepSpec]]
    check: Optional[Callable[[dict], None]] = None

    def validate(self, config: Optional[dict]) -> dict:
        found = normalize(self.config_schema, config, self.id)

        if self.check is not None:
            self.check(found)

        return found

    def plan(
        self, config: Optional[dict], safety: Optional[dict] = None
    ) -> list[StepSpec]:
        return with_safety(self.steps(self.validate(config)), validate_safety(safety))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "config_schema": self.config_schema,
            "needs": list(self.needs),
        }


def _recreate(config: dict) -> list[StepSpec]:
    return [StepSpec("deploy_new", {"weight": 100}), StepSpec("retire_old")]


def _rolling(config: dict) -> list[StepSpec]:
    batch, pause = config["batch_percent"], config["pause_seconds"]
    steps: list[StepSpec] = []
    upto = 0

    while upto < 100:
        upto = min(100, upto + batch)
        steps.append(StepSpec("replace", {"batch_percent": batch, "upto": upto}))

        if upto < 100 and pause > 0:
            steps.append(StepSpec("pause", {"seconds": pause}))

    return steps


def _blue_green(config: dict) -> list[StepSpec]:
    steps = [
        StepSpec("deploy_new", {"weight": 0}),
        StepSpec("health"),
        StepSpec("shift", {"weight": 100}),
    ]

    if config["bake_seconds"] > 0:
        steps.append(
            StepSpec("pause", {"seconds": config["bake_seconds"], "reason": "bake"})
        )

    if config["keep_old_seconds"] > 0:
        steps.append(
            StepSpec(
                "pause", {"seconds": config["keep_old_seconds"], "reason": "keep_old"}
            )
        )

    return [*steps, StepSpec("retire_old")]


def _canary(config: dict) -> list[StepSpec]:
    steps = [StepSpec("deploy_new", {"weight": 0})]

    for step in config["steps"]:
        steps.append(StepSpec("shift", {"weight": step["weight"]}))

        if step["pause_seconds"] > 0:
            steps.append(StepSpec("pause", {"seconds": step["pause_seconds"]}))

        steps.append(StepSpec("health"))

    return [*steps, StepSpec("retire_old")]


def _canary_check(config: dict) -> None:
    if config["steps"][-1]["weight"] != 100:
        raise ConfigError("canary.steps must end at weight 100")


def _shadow(config: dict) -> list[StepSpec]:
    steps = [StepSpec("deploy_new", {"weight": 0}), StepSpec("mirror", {"on": True})]

    if config["duration_seconds"] > 0:
        steps.append(
            StepSpec(
                "pause", {"seconds": config["duration_seconds"], "reason": "shadow"}
            )
        )

    return [
        *steps,
        StepSpec("health"),
        StepSpec("mirror", {"on": False}),
        StepSpec("retire_old", {"retire": "new"}),
    ]


STRATEGIES: dict[str, Strategy] = {
    s.id: s
    for s in (
        Strategy(
            "recreate",
            "Recreate",
            "Ship the release in place of the one running: the deploy the target always did.",
            schema({}),
            (),
            _recreate,
        ),
        Strategy(
            "rolling",
            "Rolling",
            "Replace the running version a batch at a time, pausing between batches.",
            schema(
                {
                    "batch_percent": integer(25, 1, 100),
                    "pause_seconds": integer(60, 0),
                }
            ),
            ("replace",),
            _rolling,
        ),
        Strategy(
            "blue_green",
            "Blue-green",
            "Start the new version beside the old one, check it, move all traffic at once, keep the old one until the bake ends.",
            schema(
                {
                    "bake_seconds": integer(300, 0),
                    "keep_old_seconds": integer(0, 0),
                }
            ),
            ("deploy_new", "health", "shift", "retire_old"),
            _blue_green,
        ),
        Strategy(
            "canary",
            "Canary",
            "Send a growing share of traffic to the new version, checking its health after each step.",
            schema(
                {
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "weight": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100,
                                },
                                "pause_seconds": {"type": "integer", "minimum": 0},
                            },
                            "required": ["weight", "pause_seconds"],
                            "additionalProperties": False,
                        },
                        "default": CANARY_STEPS,
                    }
                }
            ),
            ("deploy_new", "shift", "health", "retire_old"),
            _canary,
            _canary_check,
        ),
        Strategy(
            "shadow",
            "Shadow",
            "Mirror live traffic to the new version without serving its answers, then remove it: the old version keeps serving.",
            schema({"duration_seconds": integer(600, 0)}),
            ("deploy_new", "mirror", "health", "retire_old"),
            _shadow,
        ),
    )
}
DEFAULT = "recreate"


def strategy(id: Optional[str]) -> Strategy:
    found = STRATEGIES.get(id or DEFAULT)

    if found is None:
        raise ConfigError(
            f"no deployment strategy {id!r} (strategies: {', '.join(STRATEGIES)})"
        )

    return found


def validate_safety(safety: Optional[dict]) -> dict:
    return normalize(SAFETY_SCHEMA, safety, "safety")


def with_safety(steps: list[StepSpec], safety: dict) -> list[StepSpec]:
    """`manual_approval` waits before the first traffic step (before deploy_new when there is none); `bake_seconds` waits before the old version is retired."""
    steps = list(steps)

    if safety["bake_seconds"] > 0:
        at = next(
            (i for i in range(len(steps) - 1, -1, -1) if steps[i].kind == "retire_old"),
            len(steps),
        )
        steps.insert(
            at, StepSpec("pause", {"seconds": safety["bake_seconds"], "reason": "bake"})
        )

    if safety["manual_approval"]:
        at = next(
            (i for i, s in enumerate(steps) if s.kind in TRAFFIC),
            next((i for i, s in enumerate(steps) if s.kind == "deploy_new"), 0),
        )
        steps.insert(at, StepSpec("approval", {"reason": "manual_approval"}))

    return steps


def native_plan(id: str, config: dict, safety: dict) -> list[StepSpec]:
    steps = [StepSpec("native", {"strategy": id, "config": config})]

    if safety["manual_approval"]:
        steps.insert(0, StepSpec("approval", {"reason": "manual_approval"}))

    return steps


def catalog() -> dict[str, Any]:
    return {
        "strategies": [s.as_dict() for s in STRATEGIES.values()],
        "safety_schema": SAFETY_SCHEMA,
    }


__all__ = [
    "CANARY_STEPS",
    "DEFAULT",
    "SAFETY_SCHEMA",
    "STEP_KINDS",
    "STRATEGIES",
    "StepSpec",
    "Strategy",
    "catalog",
    "native_plan",
    "normalize",
    "strategy",
    "validate_safety",
    "with_safety",
]
