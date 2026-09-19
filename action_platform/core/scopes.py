"""Scopes: where a release is deployed, each with a kind and a criticality that decides which releases it accepts.

    [[scopes]]
    name = "prod"
    kind = "web"
    criticality = "high"

No scope, no deploy: a repository without `[[scopes]]` releases but does not deploy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_platform.core.context import Check
from action_platform.core.exception import ConfigError

CRITICALITIES = ("test", "low", "medium", "high", "critical")
KINDS = ("web", "job", "worker", "static", "library")
SHAPES = ("candidate", "stable", "hotfix")

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
    """Every `[[scopes]]` entry of platform.toml; none when the table is absent."""
    return [_scope(item) for item in data.get("scopes") or []]


def _scope(item: Any) -> ScopeSpec:
    if not isinstance(item, dict) or not item.get("name"):
        raise ConfigError("[[scopes]] needs a name")

    kind = str(item.get("kind") or "web")
    criticality = str(item.get("criticality") or "low")

    if kind not in KINDS:
        raise ConfigError(
            f"scope {item['name']!r}: kind {kind!r} is not one of {', '.join(KINDS)}"
        )

    rank(criticality)

    return ScopeSpec(name=str(item["name"]), kind=kind, criticality=criticality)
