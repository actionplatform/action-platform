"""Scopes: where a release is deployed, each with a kind and a criticality that decides which releases it accepts.

    [[scopes]]
    name = "prod"
    kind = "web"
    criticality = "high"
    target = "aws/lambda"
    region = "us-east-1"

Without `[[scopes]]`, the `[deploy]` targets read as scopes: one per stage a target names, else `dev` (test) and `prod` (high)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from action_platform.core.context import Check
from action_platform.core.exception import ConfigError
from action_platform.core.targets import EXECUTORS, parse_targets

CRITICALITIES = ("test", "low", "medium", "high", "critical")
KINDS = ("web", "job", "worker", "static", "library")
SHAPES = ("candidate", "stable", "hotfix")
RESERVED = {"name", "kind", "criticality", "target", "run_by", "url"}

DEFAULT_CRITICALITY = {"dev": "test", "prod": "high"}
DEFAULT_POLICY: dict[str, frozenset[str]] = {
    "test": frozenset(SHAPES),
    "low": frozenset(SHAPES),
    "medium": frozenset({"stable", "hotfix"}),
    "high": frozenset({"stable", "hotfix"}),
    "critical": frozenset({"stable", "hotfix"}),
}


@dataclass(frozen=True)
class ScopeSpec:
    name: str
    kind: str = "web"
    criticality: str = "low"
    target: str = ""
    run_by: str = "platform"
    url: Optional[str] = None
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def level(self) -> int:
        return CRITICALITIES.index(self.criticality)


def rank(criticality: str) -> int:
    if criticality not in CRITICALITIES:
        raise ConfigError(
            f"criticality {criticality!r} is not one of {', '.join(CRITICALITIES)}"
        )

    return CRITICALITIES.index(criticality)


def shape_of(version: str, branch: Optional[str] = None) -> str:
    """`hotfix` when cut from a `hotfix/*` branch, `candidate` when the version carries a pre-release part, `stable` otherwise."""
    if branch and branch.startswith("hotfix/"):
        return "hotfix"

    core = version.lstrip("v").split("+", 1)[0]

    return "candidate" if "-" in core else "stable"


def accepts(
    criticality: str, shape: str, policy: Optional[dict[str, Any]] = None
) -> bool:
    rank(criticality)

    if shape not in SHAPES:
        raise ConfigError(f"release shape {shape!r} is not one of {', '.join(SHAPES)}")

    allowed = (policy or DEFAULT_POLICY).get(criticality)

    return shape in (allowed if allowed is not None else DEFAULT_POLICY[criticality])


def shape_check(
    scope: ScopeSpec, version: str, shape: str, policy: Optional[dict[str, Any]] = None
) -> Check:
    ok = accepts(scope.criticality, shape, policy)

    return Check(
        "scope.release-shape",
        ok,
        f"{version} is a {shape} release; {scope.name} is {scope.criticality}"
        + (
            ""
            if ok
            else f" and takes {', '.join(sorted((policy or DEFAULT_POLICY)[scope.criticality]))} only"
        ),
        level="static",
        fix=None
        if ok
        else "deploy it to a scope of lower criticality, or cut a stable release",
    )


def parse_scopes(data: dict) -> list[ScopeSpec]:
    """Every scope of platform.toml: `[[scopes]]` when present, else the `[deploy]` targets as scopes."""
    raw = data.get("scopes")

    if raw:
        return [_scope(item) for item in raw]

    return derived_scopes(data.get("deploy") or {})


def derived_scopes(deploy: dict) -> list[ScopeSpec]:
    """The `[deploy]` targets as scopes; an app with no target at all still has `dev` and `prod`, with no target to run."""
    specs: list[ScopeSpec] = []
    targets = parse_targets(deploy)

    if not targets:
        return [
            ScopeSpec(name=stage, criticality=DEFAULT_CRITICALITY[stage])
            for stage in DEFAULT_CRITICALITY
        ]

    for target in targets:
        stages = target.stages or ("dev", "prod")

        for stage in stages:
            specs.append(
                ScopeSpec(
                    name=stage
                    if len(stages) > 1 or stage in DEFAULT_CRITICALITY
                    else target.name,
                    kind="library" if target.kind in ("pypi", "npm") else "web",
                    criticality=DEFAULT_CRITICALITY.get(stage, "low"),
                    target=target.kind,
                    run_by=target.run_by,
                    options=dict(target.options),
                )
            )

    seen: dict[str, ScopeSpec] = {}

    for spec in specs:
        seen.setdefault(spec.name, spec)

    return list(seen.values())


def _scope(item: Any) -> ScopeSpec:
    if not isinstance(item, dict) or not item.get("name"):
        raise ConfigError("[[scopes]] needs a name")

    kind = str(item.get("kind") or "web")
    criticality = str(item.get("criticality") or "low")
    run_by = str(item.get("run_by") or "platform")

    if kind not in KINDS:
        raise ConfigError(
            f"scope {item['name']!r}: kind {kind!r} is not one of {', '.join(KINDS)}"
        )

    rank(criticality)

    if run_by not in EXECUTORS:
        raise ConfigError(
            f"scope {item['name']!r}: run_by {run_by!r} is not one of {', '.join(EXECUTORS)}"
        )

    return ScopeSpec(
        name=str(item["name"]),
        kind=kind,
        criticality=criticality,
        target=str(item.get("target") or ""),
        run_by=run_by,
        url=item.get("url") or None,
        options={k: v for k, v in item.items() if k not in RESERVED},
    )
