"""Roles, permissions and token scopes: the one place that says who may do what."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

ROLES = ("owner", "admin", "deployer", "developer", "viewer")
PERMISSIONS = (
    "org.manage",
    "project.manage",
    "app.release",
    "app.configure",
    "app.flow",
    "app.sync",
)
SCOPES = ("read", "write", "release", "admin")

GRANTS: dict[str, tuple[str, ...]] = {
    "owner": PERMISSIONS,
    "admin": PERMISSIONS,
    "deployer": ("app.release", "app.configure", "app.flow", "app.sync"),
    "developer": ("app.configure", "app.flow", "app.sync"),
    "viewer": (),
}

SCOPE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "read": (),
    "write": ("app.configure", "app.flow", "app.sync"),
    "release": ("app.release",),
    "admin": ("project.manage", "org.manage"),
}

DEFAULT_SCOPES = ("read", "write")

ROLE_LABELS = {
    "owner": "Owner",
    "admin": "Admin",
    "deployer": "Deployer",
    "developer": "Developer",
    "viewer": "Viewer",
}

ROLE_DESCRIPTIONS = {
    "owner": "Everything, including deleting the organization. At least one per organization.",
    "admin": "Members, teams, code hosts, projects and every app action.",
    "deployer": "Cuts releases and edits configuration, plus everything a developer can do.",
    "developer": "Branches, pull requests, commits and sync. No releases.",
    "viewer": "Read-only access to projects, apps, releases and activity.",
}

PERMISSION_DESCRIPTIONS = {
    "org.manage": "Manage members, teams, code hosts and settings",
    "project.manage": "Create and delete projects, add and remove apps",
    "app.release": "Create releases",
    "app.configure": "Edit configuration, deploy target, services and commit",
    "app.flow": "Start branches, check out, push and open pull requests",
    "app.sync": "Sync workspaces with the code host",
}

SCOPE_INFO = {
    "read": ("Read", "List projects, apps, releases, branches and activity"),
    "write": ("Write", "Configuration, branches, pull requests, commits and sync"),
    "release": ("Release", "Create releases"),
    "admin": ("Admin", "Projects, apps, members, code hosts and settings"),
}


def normalize_role(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    if value == "member":
        return "developer"

    return value if value in ROLES else None


def can(role: Optional[str], permission: str) -> bool:
    normalized = normalize_role(role)

    return bool(normalized) and permission in GRANTS[normalized]


def grants_of(role: Optional[str]) -> dict[str, bool]:
    return {p: can(role, p) for p in PERMISSIONS}


def parse_scopes(value: Optional[str]) -> list[str]:
    parts = {p for p in (value or "").replace(",", " ").split() if p in SCOPES}

    return [s for s in SCOPES if s in parts]


def scope_allows(scopes: list[str], permission: Optional[str]) -> bool:
    if "read" not in scopes:
        return False

    if permission is None:
        return True

    return any(permission in SCOPE_PERMISSIONS[s] for s in scopes)


def grantable_scopes(role: Optional[str]) -> list[str]:
    return [
        s
        for s in SCOPES
        if s == "read" or all(can(role, p) for p in SCOPE_PERMISSIONS[s])
    ]


@dataclass(frozen=True)
class Grant:
    """What a token may reach: scopes, one organization or all, optionally one project or one app."""

    scope: list[str] = field(default_factory=list)
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None

    def format(self) -> str:
        parts = list(self.scope)

        if self.organization_id:
            parts.append(f"org:{self.organization_id}")

        if self.project_id:
            parts.append(f"project:{self.project_id}")

        if self.app_id:
            parts.append(f"app:{self.app_id}")

        return " ".join(parts)

    @classmethod
    def parse(cls, value: Optional[str]) -> "Grant":
        ids: dict[str, Optional[str]] = {"org": None, "project": None, "app": None}

        for part in (value or "").replace(",", " ").split():
            key, _, id = part.partition(":")

            if id and key in ids:
                ids[key] = id

        return cls(parse_scopes(value), ids["org"], ids["project"], ids["app"])


def catalog() -> dict:
    """The whole rule table, for anything that wants to display it."""
    return {
        "roles": [
            {
                "id": role,
                "label": ROLE_LABELS[role],
                "description": ROLE_DESCRIPTIONS[role],
                "permissions": list(GRANTS[role]),
                "grantable_scopes": grantable_scopes(role),
            }
            for role in ROLES
        ],
        "permissions": [
            {"id": p, "description": PERMISSION_DESCRIPTIONS[p]} for p in PERMISSIONS
        ],
        "scopes": [
            {
                "id": scope,
                "label": SCOPE_INFO[scope][0],
                "description": SCOPE_INFO[scope][1],
                "permissions": list(SCOPE_PERMISSIONS[scope]),
            }
            for scope in SCOPES
        ],
        "default_scopes": list(DEFAULT_SCOPES),
    }
