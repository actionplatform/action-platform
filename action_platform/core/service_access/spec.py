"""The values every part shares: a `Grant` (who has what on which service), an `Op` that changes one, a `Person` of the organization and the `Mapping` that ties people to their accounts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Action = Literal["add", "change", "remove"]


@dataclass(frozen=True, order=True)
class Grant:
    service: str
    account: str
    resource: str
    level: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.service, self.account.lower(), self.resource)

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def of(cls, row: dict[str, Any]) -> "Grant":
        return cls(
            str(row["service"]),
            str(row["account"]),
            str(row["resource"]),
            str(row["level"]),
        )


@dataclass(frozen=True)
class Op:
    action: Action
    grant: Grant
    previous: str = ""

    def describe(self) -> str:
        g = self.grant

        if self.action == "change":
            return f"{g.service}: {g.account} {g.resource} {self.previous} -> {g.level}"

        return f"{g.service}: {self.action} {g.account} {g.resource} {g.level}"


@dataclass(frozen=True)
class Person:
    email: str
    user_id: str
    name: str
    role: str
    teams: tuple[str, ...] = ()


@dataclass
class Mapping:
    """What the organization decided: `people` links a member's email to an account per service, `roles` and `teams` name the grants a platform role or team carries, `grants` the ones given to one person, `keep` the access of accounts outside the organization left as found, `imported` when each service's live state was imported."""

    people: dict[str, dict[str, str]] = field(default_factory=dict)
    roles: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    teams: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    grants: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    keep: list[dict[str, str]] = field(default_factory=list)
    imported: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def of(cls, data: Any) -> "Mapping":
        if not isinstance(data, dict):
            return cls()

        return cls(
            people={k: dict(v) for k, v in (data.get("people") or {}).items()},
            roles={k: list(v) for k, v in (data.get("roles") or {}).items()},
            teams={k: list(v) for k, v in (data.get("teams") or {}).items()},
            grants={k: list(v) for k, v in (data.get("grants") or {}).items()},
            keep=list(data.get("keep") or []),
            imported={k: str(v) for k, v in (data.get("imported") or {}).items()},
        )

    def account(self, email: str, service: str) -> str:
        return self.people.get(email.lower(), {}).get(service, "")

    def owner_of(self, service: str, account: str) -> str:
        for email, ids in self.people.items():
            if ids.get(service, "").lower() == account.lower():
                return email

        return ""


def spec(service: str, resource: str, level: str) -> dict[str, str]:
    return {"service": service, "resource": resource, "level": level}
