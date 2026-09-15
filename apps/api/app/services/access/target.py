"""What a /api/v1 call is aimed at — the rule, the organization, the app — and whether the caller may aim there: role ∩ scope ∩ reach."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.access.rules import Rule, rule_for
from app.core.db.models import App, Organization, Project
from app.core.errors import Refused
from app.services.access.caller import Caller
from app.services.directory import DirectoryService


@dataclass
class Target:
    rule: Rule
    organization: Optional[Organization]
    app: Optional[App]
    project: Optional[Project]


def requested_organization(
    caller: Caller, headers: dict[str, str]
) -> Optional[Organization]:
    wanted = (headers.get("x-organization") or "").strip()

    if wanted and (caller.all_organizations or caller.scope is None):
        found = caller.member_of(wanted)

        if found is not None:
            return found

    return caller.organization


class Authorizer:
    def __init__(self, directory: DirectoryService) -> None:
        self.directory = directory

    def target(
        self, caller: Caller, method: str, path: str, headers: dict[str, str]
    ) -> Target:
        rule = rule_for(method, path)

        if rule is None:
            raise Refused(404, f"{method} /api/v1/{path} is not exposed")

        listing = method == "GET" and path == "apps"
        segments = path.split("/")
        registry_id = (
            segments[1]
            if path.startswith("apps/") and len(segments) > 1 and segments[1] != "init"
            else None
        )
        app: Optional[App] = None
        project: Optional[Project] = None
        organization: Optional[Organization] = None

        if registry_id:
            found = self.directory.app_by_registry_id(registry_id)

            if found:
                app, project = found
                organization = caller.member_of(project.organization_id)

            if (
                app is None
                or organization is None
                or (caller.organization and caller.organization.id != organization.id)
            ):
                raise Refused(404, "app not found")
        else:
            organization = requested_organization(caller, headers) or (
                None if listing else caller.organization
            )

            if organization is None and not listing:
                raise Refused(
                    400,
                    "this token spans every organization: send X-Organization: <id or slug>",
                )

        ok, why = caller.allows(
            organization.id if organization else None, rule.permission
        )

        if not ok:
            raise Refused(403, why)

        if (
            app is not None
            and project is not None
            and not caller.within_reach(app.id, project.id)
        ):
            raise Refused(404, "app not found")

        if (
            app is None
            and method == "POST"
            and path in ("apps", "apps/init")
            and (caller.project_id or caller.app_id)
        ):
            raise Refused(
                403, "this token is limited to one project; it cannot add apps"
            )

        return Target(rule, organization, app, project)

    def reach(self, caller: Caller, organization: Optional[Organization]) -> set[str]:
        """The registry ids the caller may list."""
        allowed: set[str] = set()

        for org in (
            [organization] if organization else [o for o, _ in caller.organizations]
        ):
            allowed |= self.directory.registry_ids_of(
                org.id, caller.project_id, caller.app_id
            )

        return allowed
