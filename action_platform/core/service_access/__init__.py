"""Access on the services a team uses — GitHub, Jenkins, Sentry, Dokploy… — mapped from the organization's members, roles and teams. Each service's plugin brings an `AccessProvider`; the engine reads live state, diffs it against the mapping and applies the changes."""

from action_platform.core.service_access.engine import Access
from action_platform.core.service_access.http import Http, Response
from action_platform.core.service_access.models import (
    Audit,
    Change,
    GrantRow,
    PersonOut,
    Plan,
    ServiceAudit,
    Who,
)
from action_platform.core.service_access.provider import (
    AccessError,
    AccessProvider,
    Directory,
)
from action_platform.core.service_access.spec import (
    Grant,
    Mapping,
    Op,
    Person,
    spec,
)

__all__ = [
    "Access",
    "AccessError",
    "AccessProvider",
    "Audit",
    "Change",
    "Directory",
    "Grant",
    "GrantRow",
    "Http",
    "Mapping",
    "Op",
    "Person",
    "PersonOut",
    "Plan",
    "Response",
    "ServiceAudit",
    "Who",
    "spec",
]
