"""From the organization and its mapping to the grants each service should hold, and from there to the changes that close the gap."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from action_platform.core.service_access.provider import AccessProvider as Provider
from action_platform.core.service_access.spec import Grant, Mapping, Op, Person, spec


def sources(mapping: Mapping, person: Person) -> list[tuple[str, dict[str, str]]]:
    """Every grant spec that applies to the person, with where it comes from: `role:<role>`, `team:<slug>` or `person`."""
    found = [(f"role:{person.role}", s) for s in mapping.roles.get(person.role, [])]

    for team in person.teams:
        found += [(f"team:{team}", s) for s in mapping.teams.get(team, [])]

    found += [("person", s) for s in mapping.grants.get(person.email, [])]

    return found


def desired(
    mapping: Mapping,
    people: Iterable[Person],
    providers: dict[str, Provider],
    policy_only: bool = False,
) -> dict[str, set[Grant]]:
    wanted: dict[str, list[Grant]] = {name: [] for name in providers}

    for person in people:
        for origin, s in sources(mapping, person):
            if policy_only and origin == "person":
                continue

            service = s["service"]
            account = mapping.account(person.email, service)

            if service in wanted and account:
                wanted[service].append(
                    Grant(service, account, s["resource"], s["level"])
                )

    if not policy_only:
        for row in mapping.keep:
            g = Grant.of(row)

            if g.service in wanted:
                wanted[g.service].append(g)

    return {
        name: provider.expand(set(provider.strongest(wanted[name])))
        for name, provider in providers.items()
    }


def diff(
    want: set[Grant], live: Iterable[Grant], accounts: Optional[set[str]] = None
) -> list[Op]:
    """The changes that turn `live` into `want`; with `accounts`, only those accounts are touched."""
    have = {g.key: g for g in live}
    target = {g.key: g for g in want}
    ops: list[Op] = []

    for key, g in sorted(target.items()):
        if accounts is not None and g.account.lower() not in accounts:
            continue

        current = have.get(key)

        if current is None:
            ops.append(Op("add", g))
        elif current.level != g.level:
            ops.append(Op("change", g, current.level))

    for key, g in sorted(have.items()):
        if accounts is not None and g.account.lower() not in accounts:
            continue

        if key not in target:
            ops.append(Op("remove", g))

    return ops


def bootstrap(
    mapping: Mapping,
    people: list[Person],
    live: dict[str, list[Grant]],
    providers: dict[str, Provider],
    links: Optional[dict[str, dict[str, str]]] = None,
) -> Mapping:
    """Import what each service holds today: link members to accounts (given links, then the ones already known, then an email that is the account itself), record each linked member's access that no role or team explains as their own grants, and keep every other account's access as found. Only the services in `live` are imported; a sync right after changes nothing on them."""
    result = Mapping.of(mapping.as_dict())
    emails = {p.email for p in people}

    for service, grants in live.items():
        accounts = {g.account.lower(): g.account for g in grants}

        for email, ids in (links or {}).items():
            if service in ids:
                found = accounts.get(ids[service].lower(), ids[service])
                result.people.setdefault(email.lower(), {})[service] = found

        for person in people:
            if not result.account(person.email, service) and person.email in accounts:
                result.people.setdefault(person.email, {})[service] = accounts[
                    person.email
                ]

    from_policy = desired(result, people, providers, policy_only=True)
    result.grants = {
        email: kept
        for email, specs in result.grants.items()
        if (kept := [s for s in specs if s["service"] not in live])
    }
    result.keep = [row for row in result.keep if row["service"] not in live]

    for service, grants in live.items():
        explained = {g.key: g for g in from_policy.get(service, set())}

        for g in grants:
            owner = result.owner_of(service, g.account)

            if owner and owner in emails:
                kept = explained.get(g.key)

                if kept is None or kept.level != g.level:
                    result.grants.setdefault(owner, []).append(
                        spec(service, g.resource, g.level)
                    )
            else:
                result.keep.append(g.as_dict())

    moment = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result.imported.update({service: moment for service in live})

    return result
