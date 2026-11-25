"""Access on the organization's services — GitHub, built in, and those its plugins own: who has what, drift, grant, revoke, offboard, sync. Reads are safe; every change is a dry run until `apply` is true."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.service_access.models import Audit, Plan, Who
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import OrgId
from action_platform.remote.client import Remote

Person = Annotated[
    str,
    Field(description="The member's email on the platform (or user id, or exact name)"),
]
Service = Annotated[
    str,
    Field(
        description="A service as access_audit names it: github, built in, or one a plugin brings access for (jenkins, sentry, dokploy…)"
    ),
]
Apply = Annotated[
    bool,
    Field(
        description="False shows the plan; true changes the service. Show the plan and ask first."
    ),
]


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def access_audit(
        service: Annotated[
            Optional[str], Field(description="Only this service")
        ] = None,
        organization: OrgId = None,
    ) -> Audit:
        """Drift per service: what each service holds against what the organization's members, roles and teams ask for — what a sync would change, members with no account linked, accounts that belong to no member, and the resources and levels each service grants. Needs org.manage."""
        return remote.access_audit(service, organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def access_who(
        person: Annotated[
            Optional[str],
            Field(
                description="A member's email: their accounts and access on every service"
            ),
        ] = None,
        service: Annotated[
            Optional[str],
            Field(
                description="A service: every account with access there and the member it belongs to"
            ),
        ] = None,
        organization: OrgId = None,
    ) -> Who:
        """Who has access to what. Give a person to see their accounts, live grants and drift on each service; give a service to list every account with access there. Needs org.manage."""
        return remote.access_who(person, service, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def access_grant(
        person: Person,
        service: Service,
        resource: Annotated[
            str,
            Field(
                description="`<kind>` or `<kind>/<name>` with a kind from the service's levels in access_audit (org, team/<slug>, repo/<name>, folder/<name>…)"
            ),
        ],
        level: Annotated[
            str,
            Field(description="One of the levels access_audit lists for that kind"),
        ],
        account: Annotated[
            Optional[str],
            Field(
                description="The person's account on the service (login, user id or email) when the mapping has none yet"
            ),
        ] = None,
        apply: Apply = False,
        organization: OrgId = None,
    ) -> Plan:
        """Give one person access on one service and record it in the mapping. Only that person's account is touched."""
        return remote.access_grant(
            person, service, resource, level, account, apply, organization=organization
        )

    @tool(mcp, annotations=DESTRUCTIVE)
    def access_revoke(
        person: Person,
        service: Service,
        resource: Annotated[
            str, Field(description="The resource as access_who shows it")
        ],
        apply: Apply = False,
        organization: OrgId = None,
    ) -> Plan:
        """Take one grant away from one person and drop it from the mapping. Access that comes from the person's role or team stays; the answer says which."""
        return remote.access_revoke(
            person, service, resource, apply, organization=organization
        )

    @tool(mcp, annotations=DESTRUCTIVE)
    def access_offboard(
        person: Person,
        apply: Apply = False,
        remove_from_platform: Annotated[
            bool,
            Field(
                description="Also remove the member from the organization on the platform"
            ),
        ] = False,
        organization: OrgId = None,
    ) -> Plan:
        """Remove a person everywhere: every grant of every linked account on every service, their entries in the mapping, and optionally their platform membership. The last administrator of a service is never removed."""
        return remote.access_offboard(
            person, apply, remove_from_platform, organization=organization
        )

    @tool(mcp, annotations=DESTRUCTIVE)
    def access_sync(
        service: Annotated[
            Optional[str], Field(description="Only this service")
        ] = None,
        apply: Apply = False,
        reimport: Annotated[
            bool,
            Field(
                description="Import live state into the mapping again instead of changing the services"
            ),
        ] = False,
        links: Annotated[
            Optional[dict[str, dict[str, str]]],
            Field(
                description="With an import: {member email: {service: account}} for accounts that are not the member's email (GitHub logins, Jenkins ids)"
            ),
        ] = None,
        organization: OrgId = None,
    ) -> Plan:
        """Make every service match the mapping. A service not imported yet is only imported — what it holds today goes into the mapping and nothing there is changed or removed; an imported service gets the adds, changes and removes that close the drift access_audit shows."""
        return remote.access_sync(
            service, apply, reimport, links, organization=organization
        )
