"""What the hosted platform tells a plugin happened: the event envelope a plugin's `routes` and `deliver` receive."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Optional

EVENT_KINDS = (
    "release.created",
    "deployment.started",
    "deployment.succeeded",
    "deployment.failed",
    "deployment.verified",
    "readiness.blocked",
    "ci.failed",
)


@dataclass(frozen=True)
class Event:
    """One thing that happened in an organization: `kind` from `EVENT_KINDS`, the organization's slug, the project's slug and the app's name it happened to, who did it when someone did, what it carries (`payload`, per kind) and the platform page that shows it (`url`)."""

    kind: str
    organization: str
    project: str = ""
    app: str = ""
    actor: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    url: Optional[str] = None
    id: str = ""
    at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        known = {f.name for f in fields(cls)}

        return cls(**{k: v for k, v in data.items() if k in known})
