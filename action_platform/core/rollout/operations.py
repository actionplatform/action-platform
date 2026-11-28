"""What a deploy target answers when a strategy asks it for one step: the operation ids, the context each call receives and the result it returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from action_platform.core.context import Context

OPERATIONS = (
    "deploy_new",
    "shift",
    "mirror",
    "replace",
    "retire_old",
    "rollback",
    "health",
    "status",
)
STATES = ("running", "succeeded", "failed")


@dataclass
class OperationResult:
    """`ok` false is a refusal or a failure the platform acts on; `data["state"]` in `STATES` says an operation is still running (it is then followed with `status`) or how one that was running ended."""

    ok: bool
    detail: str = ""
    external_ref: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def state(self) -> Optional[str]:
        found = self.data.get("state")

        return found if found in STATES else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "detail": self.detail,
            "external_ref": self.external_ref,
            "data": dict(self.data),
        }

    @classmethod
    def of(cls, raw: Optional[dict[str, Any]]) -> Optional["OperationResult"]:
        if not raw:
            return None

        return cls(
            ok=bool(raw.get("ok")),
            detail=str(raw.get("detail") or ""),
            external_ref=raw.get("external_ref"),
            data=dict(raw.get("data") or {}),
        )


@dataclass
class OperationContext:
    """One call of one step: the app, the release and the scope, the strategy's config, the step's params, and `deploy` — the same Context a deploy receives, with the environment, the identity and the repository at the release tag."""

    app: str
    tag: str
    version: str
    scope: str
    strategy: str
    deploy: Context
    config: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    operation: str = ""
    deployment_id: str = ""
    step: int = 0
    external_ref: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def env(self) -> dict[str, str]:
        return self.deploy.env

    def identity_token(self, audience: str) -> Optional[str]:
        return self.deploy.identity_token(audience)


__all__ = ["OPERATIONS", "STATES", "OperationContext", "OperationResult"]
