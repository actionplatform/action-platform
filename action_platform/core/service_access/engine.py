"""The six operations behind the routes, the tools and the commands: who, audit, grant, revoke, offboard, sync. Dry runs unless `apply`; a service is imported, never changed, by the sync that first sees it."""

from __future__ import annotations

from typing import Optional

from action_platform.core.service_access.provider import (
    AccessError,
    AccessProvider as Provider,
    Directory,
)
from action_platform.core.service_access.models import (
    Audit,
    Change,
    GrantRow,
    PersonOut,
    Plan,
    ServiceAudit,
    Who,
)
from action_platform.core.service_access.policy import bootstrap, desired, diff, sources
from action_platform.core.service_access.spec import Grant, Mapping, Op, Person, spec


class Access:
    def __init__(
        self,
        directory: Directory,
        providers: dict[str, Provider],
        errors: Optional[dict[str, str]] = None,
    ) -> None:
        self.directory = directory
        self.providers = providers
        self.unavailable = dict(errors or {})

    def audit(self, service: Optional[str] = None) -> Audit:
        mapping, people = self.directory.load(), self.directory.people()
        providers = self._pick(service)
        live, errors = self._live(providers)
        want = desired(mapping, people, providers)
        rows = []

        for name in sorted(set(providers) | self._missing(service)):
            if name not in live:
                rows.append(
                    ServiceAudit(
                        service=name,
                        ok=False,
                        levels=self._levels(name),
                        error=errors.get(name) or self.unavailable.get(name),
                        imported=name in mapping.imported,
                    )
                )
                continue

            if name not in mapping.imported:
                rows.append(
                    ServiceAudit(
                        service=name,
                        ok=True,
                        imported=False,
                        levels=self._levels(name),
                        live=len(live[name]),
                        outside_accounts=sorted({g.account for g in live[name]}),
                    )
                )
                continue

            ops = diff(want[name], live[name])
            linked = {mapping.account(p.email, name).lower() for p in people} - {""}
            rows.append(
                ServiceAudit(
                    service=name,
                    ok=True,
                    levels=self._levels(name),
                    live=len(live[name]),
                    wanted=len(want[name]),
                    drift=self._changes(providers[name], ops, live[name]),
                    members_without_account=sorted(
                        p.email for p in people if not mapping.account(p.email, name)
                    ),
                    outside_accounts=sorted(
                        {
                            g.account
                            for g in live[name]
                            if g.account.lower() not in linked
                        }
                    ),
                )
            )

        return Audit(
            organization_members=len(people),
            imported=sorted(mapping.imported),
            services=rows,
        )

    def who(self, person: Optional[str] = None, service: Optional[str] = None) -> Who:
        if not person and not service:
            raise AccessError("name a person (email) or a service")

        mapping, people = self.directory.load(), self.directory.people()
        providers = self._pick(service)
        live, errors = self._live(providers)
        result = Who(service=service, errors=[f"{k}: {v}" for k, v in errors.items()])

        if person:
            found = self._person(person, people, mapping)
            result.person = self._out(found, mapping, people)
            accounts = {name: mapping.account(found.email, name) for name in providers}
            want = desired(mapping, [found], providers)
            origin = {
                (s["service"], s["resource"]): o for o, s in sources(mapping, found)
            }

            for name, grants in live.items():
                account = accounts.get(name, "")

                if not account:
                    continue

                for g in grants:
                    if g.account.lower() == account.lower():
                        result.grants.append(
                            self._row(g, found.email, origin.get((name, g.resource)))
                        )

                ops = diff(want[name], grants, {account})
                result.drift += self._changes(providers[name], ops, grants)
        else:
            for name, grants in live.items():
                kept = {Grant.of(r).key for r in mapping.keep}

                for g in grants:
                    owner = mapping.owner_of(name, g.account)
                    result.grants.append(
                        self._row(g, owner or None, "kept" if g.key in kept else None)
                    )

        return result

    def sync(
        self,
        service: Optional[str] = None,
        apply: bool = False,
        reimport: bool = False,
        links: Optional[dict[str, dict[str, str]]] = None,
    ) -> Plan:
        mapping, people = self.directory.load(), self.directory.people()
        providers = self._pick(service)
        live, errors = self._live(providers)
        problems = [f"{k}: {v}" for k, v in errors.items()]

        fresh = {
            name: grants
            for name, grants in live.items()
            if reimport or links or name not in mapping.imported
        }
        proposed = (
            bootstrap(mapping, people, fresh, providers, links) if fresh else mapping
        )
        want = desired(proposed, people, providers)
        changes = []

        for name, grants in live.items():
            if name not in fresh:
                changes += self._run(
                    providers[name], diff(want[name], grants), grants, apply
                )

        if apply and fresh:
            self.directory.save(proposed)

        note = None

        if fresh:
            names = ", ".join(sorted(fresh))
            note = (
                f"Imported what {names} holds today into the mapping; nothing was changed there."
                if apply
                else f"Would import what {names} holds today into the mapping and change nothing there; run again with apply to store it."
            )

        return Plan(
            dry_run=not apply,
            bootstrap=bool(fresh),
            imported=sorted(fresh),
            changes=changes,
            errors=problems,
            mapping=proposed.as_dict() if fresh else None,
            note=note,
        )

    def grant(
        self,
        person: str,
        service: str,
        resource: str,
        level: str,
        account: Optional[str] = None,
        apply: bool = False,
    ) -> Plan:
        provider = self._provider(service)
        why = provider.valid(resource, level)

        if why:
            raise AccessError(why)

        mapping, people = self._ready(service)
        found = self._person(person, people, mapping)

        if account:
            mapping.people.setdefault(found.email, {})[service] = account

        if not mapping.account(found.email, service):
            raise AccessError(
                f"{found.email} has no {service} account in the mapping; pass account"
            )

        specs = [
            s
            for s in mapping.grants.get(found.email, [])
            if (s["service"], s["resource"]) != (service, resource)
        ]
        specs.append(spec(service, resource, level))
        held = {
            s["resource"] for _, s in sources(mapping, found) if s["service"] == service
        } | {s["resource"] for s in specs if s["service"] == service}

        for needed, needed_level in provider.companions(resource):
            if needed not in held:
                specs.append(spec(service, needed, needed_level))

        mapping.grants[found.email] = specs

        return self._personal(mapping, people, found, service, apply)

    def revoke(
        self, person: str, service: str, resource: str, apply: bool = False
    ) -> Plan:
        self._provider(service)
        mapping, people = self._ready(service)
        found = self._person(person, people, mapping)
        own = mapping.grants.get(found.email, [])
        kept = [s for s in own if (s["service"], s["resource"]) != (service, resource)]
        inherited = [
            o
            for o, s in sources(mapping, found)
            if o != "person" and (s["service"], s["resource"]) == (service, resource)
        ]

        if len(kept) == len(own) and not inherited:
            raise AccessError(
                f"{found.email} has no {service} {resource} in the mapping"
            )

        mapping.grants[found.email] = kept
        plan = self._personal(mapping, people, found, service, apply)

        if inherited:
            plan.note = f"Still granted through {', '.join(inherited)}: change the person's role or team on the platform to take it away."

        return plan

    def offboard(
        self, person: str, apply: bool = False, remove_from_platform: bool = False
    ) -> Plan:
        mapping, people = self._ready()
        found = self._person(person, people, mapping)
        accounts = dict(mapping.people.get(found.email, {}))
        mapping.people.pop(found.email, None)
        mapping.grants.pop(found.email, None)
        mapping.keep = [
            r
            for r in mapping.keep
            if r["account"].lower() != accounts.get(r["service"], "").lower()
        ]
        providers = {name: p for name, p in self.providers.items() if name in accounts}
        live, errors = self._live(providers)
        changes: list[Change] = []

        for name, grants in live.items():
            mine = [g for g in grants if g.account.lower() == accounts[name].lower()]
            changes += self._run(
                providers[name], [Op("remove", g) for g in mine], grants, apply
            )

        problems = [f"{k}: {v}" for k, v in errors.items()]
        note = None

        if apply:
            self.directory.save(mapping)

        if remove_from_platform and any(p.email == found.email for p in people):
            if apply:
                self.directory.remove(found)
                note = "Removed from the organization on the platform."
            else:
                note = "Would also remove the member from the organization on the platform."

        return Plan(dry_run=not apply, changes=changes, errors=problems, note=note)

    def _personal(
        self,
        mapping: Mapping,
        people: list[Person],
        found: Person,
        service: str,
        apply: bool,
    ) -> Plan:
        provider = self.providers[service]
        live = provider.read()
        account = mapping.account(found.email, service)
        want = desired(mapping, people, {service: provider})[service]
        changes = self._run(provider, diff(want, live, {account}), live, apply)

        if apply:
            self.directory.save(mapping)

        return Plan(dry_run=not apply, changes=changes)

    def _run(
        self, provider: Provider, ops: list[Op], live: list[Grant], apply: bool
    ) -> list[Change]:
        refused = provider.guard(ops, live)
        held = {
            op.grant.account.lower(): f"{op.describe()} was refused"
            for op in refused
            if provider.kind(op.grant.resource) in ("org", "global")
        }

        for op in ops:
            if op not in refused and op.grant.account.lower() in held:
                refused[op] = held[op.grant.account.lower()]

        changes = []

        for op in sorted(ops, key=provider.order):
            change = _change(op)

            if op in refused:
                change.status, change.detail = "refused", refused[op]
            elif apply:
                try:
                    provider.apply(op)
                    change.status = "applied"
                except AccessError as e:
                    change.status, change.detail = "failed", str(e)

            changes.append(change)

        return changes

    def _changes(
        self, provider: Provider, ops: list[Op], live: list[Grant]
    ) -> list[Change]:
        return self._run(provider, ops, live, False)

    def _ready(self, service: Optional[str] = None) -> tuple[Mapping, list[Person]]:
        mapping = self.directory.load()
        missing = service not in mapping.imported if service else not mapping.imported

        if missing:
            raise AccessError(
                f"{service or 'no service'} has not been imported yet: run access_sync first — it imports what each service holds today and changes nothing"
            )

        return mapping, self.directory.people()

    def _live(
        self, providers: dict[str, Provider]
    ) -> tuple[dict[str, list[Grant]], dict[str, str]]:
        live, errors = {}, {}

        for name, provider in providers.items():
            try:
                live[name] = provider.read()
            except AccessError as e:
                errors[name] = str(e)

        return live, errors

    def _pick(self, service: Optional[str]) -> dict[str, Provider]:
        if service is None:
            return dict(self.providers)

        return {service: self._provider(service)}

    def _levels(self, name: str) -> dict[str, list[str]]:
        provider = self.providers.get(name)

        if provider is None:
            return {}

        return {kind: list(levels) for kind, levels in provider.levels.items()}

    def _missing(self, service: Optional[str]) -> set[str]:
        return {s for s in self.unavailable if service in (None, s)}

    def _provider(self, service: str) -> Provider:
        if service in self.providers:
            return self.providers[service]

        raise AccessError(
            self.unavailable.get(service) or f"{service} is not configured"
        )

    def _person(self, who: str, people: list[Person], mapping: Mapping) -> Person:
        key = who.strip().lower()

        for p in people:
            if key in (p.email, p.user_id.lower(), p.name.lower()):
                return p

        if key in mapping.people:
            return Person(email=key, user_id="", name=key, role="")

        raise AccessError(
            f"{who} is neither a member of the organization nor in the mapping"
        )

    def _out(self, person: Person, mapping: Mapping, people: list[Person]) -> PersonOut:
        return PersonOut(
            email=person.email,
            name=person.name,
            role=person.role or None,
            teams=list(person.teams),
            accounts=dict(mapping.people.get(person.email, {})),
            member=any(p.email == person.email for p in people),
        )

    def _row(self, g: Grant, person: Optional[str], source: Optional[str]) -> GrantRow:
        return GrantRow(
            service=g.service,
            account=g.account,
            resource=g.resource,
            level=g.level,
            person=person,
            source=source,
        )


def _change(op: Op) -> Change:
    g = op.grant

    return Change(
        action=op.action,
        service=g.service,
        account=g.account,
        resource=g.resource,
        level=g.level,
        previous=op.previous or None,
    )
