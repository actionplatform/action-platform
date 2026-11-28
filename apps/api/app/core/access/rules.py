import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Rule:
    method: str
    pattern: re.Pattern
    permission: Optional[str]
    credentials: bool = False
    imports: bool = False


RULES = [
    Rule("GET", re.compile(r"^(version|matrix|gitflow/rules)$"), None),
    Rule("GET", re.compile(r"^apps$"), None),
    Rule("POST", re.compile(r"^apps$"), "project.manage", credentials=True),
    Rule("POST", re.compile(r"^apps/init$"), "project.manage", credentials=True),
    Rule("GET", re.compile(r"^apps/[^/]+$"), None),
    Rule(
        "GET",
        re.compile(
            r"^apps/[^/]+/(gitflow|commits|branches|branches/plan|tags|releases|changes|manifest|diagnose|pull-request|next-version)$"
        ),
        None,
    ),
    Rule("DELETE", re.compile(r"^apps/[^/]+$"), "project.manage"),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/sync$"),
        "app.sync",
        credentials=True,
        imports=True,
    ),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/release$"),
        "app.release",
        credentials=True,
        imports=True,
    ),
    Rule("POST", re.compile(r"^apps/[^/]+/deploy$"), "app.release"),
    Rule("POST", re.compile(r"^apps/[^/]+/readiness$"), None),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/(push|branches|checkout|pull-request)$"),
        "app.flow",
        credentials=True,
        imports=True,
    ),
    Rule("PUT", re.compile(r"^apps/[^/]+/(manifest|cloud)$"), "app.configure"),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/(cloud|services|install|discard|manifest/export)$"),
        "app.configure",
    ),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/commit$"),
        "app.configure",
        credentials=True,
        imports=True,
    ),
]

DIRECTORY = {
    "me",
    "access",
    "tokens",
    "organizations",
    "projects",
    "teams",
    "members",
    "teams/members",
    "projects/team",
    "members/role",
    "jobs",
    "dashboard",
}


NESTED = re.compile(r"^projects/([^/]+)/apps/([^/]+)(?:/(.+))?$")
PROJECT_APPS = re.compile(r"^projects/([^/]+)/apps$")
SERVED_BY_PROJECTS = {"releases"}
RENAMED = {"versions": "releases"}


def nested_app(method: str, path: str) -> Optional[tuple[str, str, Optional[str]]]:
    """(project, app, rest) when `path` is an app route under its project that the workspace routes serve."""
    found = NESTED.match(path)

    if found is None:
        return None

    project, app, rest = found.groups()

    if rest is None:
        return (project, app, None) if method == "GET" else None

    if rest in SERVED_BY_PROJECTS:
        return None

    rest = RENAMED.get(rest, rest)

    if rule_for(method, f"apps/{app}/{rest}") is None:
        return None

    return project, app, rest


def project_listing(method: str, path: str) -> Optional[str]:
    found = PROJECT_APPS.match(path) if method == "GET" else None

    return found.group(1) if found else None


def rule_for(method: str, path: str) -> Optional[Rule]:
    return next(
        (r for r in RULES if r.method == method and r.pattern.match(path)), None
    )


WORKSPACE_ROOTS = {"apps", "matrix", "version", "gitflow"}
