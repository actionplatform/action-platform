"""In-memory access for tests: a service that keeps its grants in a list and a directory that keeps the organization and its mapping in memory."""

from __future__ import annotations

from action_platform.core.service_access import (
    AccessError,
    AccessProvider,
    Directory,
    Grant,
    Mapping,
    Op,
    Person,
)


class MemoryProvider(AccessProvider):
    """`org` (member, admin) and `repo/<name>` (read, write); a repository grant needs organization membership, and the last `org admin` is never removed."""

    levels = {"org": ("member", "admin"), "repo": ("read", "write")}

    def __init__(self, name: str = "vault", grants: list[Grant] | None = None):
        self.name = name
        self.grants: list[Grant] = list(grants or [])
        self.applied: list[Op] = []
        self.refuse: set[str] = set()

    def add(self, account: str, resource: str, level: str) -> None:
        self.grants.append(Grant(self.name, account, resource, level))

    def read(self) -> list[Grant]:
        return list(self.grants)

    def apply(self, op: Op) -> None:
        if op.grant.account in self.refuse:
            raise AccessError(f"{self.name}: refused {op.grant.account}")

        self.applied.append(op)
        self.grants = [g for g in self.grants if g.key != op.grant.key]

        if op.action != "remove":
            self.grants.append(op.grant)

    def companions(self, resource: str) -> list[tuple[str, str]]:
        return [("org", "member")] if self.kind(resource) == "repo" else []

    def guard(self, ops: list[Op], live: list[Grant]) -> dict[Op, str]:
        admins = {g.account for g in live if g.resource == "org" and g.level == "admin"}
        leaving = {
            op.grant.account
            for op in ops
            if op.grant.resource == "org"
            and (op.action == "remove" or op.grant.level != "admin")
        }

        if admins and admins <= leaving:
            return {
                op: f"{self.name}: never the last administrator"
                for op in ops
                if op.grant.resource == "org" and op.grant.account in admins
            }

        return {}


class MemoryDirectory(Directory):
    def __init__(self, people: list[Person], mapping: Mapping | None = None):
        self.members = list(people)
        self.mapping = mapping or Mapping()
        self.saved = 0
        self.removed: list[str] = []
        self.keep_on_platform: set[str] = set()

    def people(self) -> list[Person]:
        return list(self.members)

    def load(self) -> Mapping:
        return Mapping.of(self.mapping.as_dict())

    def save(self, mapping: Mapping) -> None:
        self.mapping = Mapping.of(mapping.as_dict())
        self.saved += 1

    def check_remove(self, person: Person) -> None:
        if person.email in self.keep_on_platform:
            raise AccessError(f"{person.email} cannot leave the organization")

    def remove(self, person: Person) -> None:
        self.members = [p for p in self.members if p.email != person.email]
        self.removed.append(person.email)
