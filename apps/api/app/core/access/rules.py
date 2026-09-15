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
    Rule("GET", re.compile(r"^(version|matrix|plugins|gitflow/rules)$"), None),
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
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/(push|branches|checkout|pull-request)$"),
        "app.flow",
        credentials=True,
        imports=True,
    ),
    Rule("PUT", re.compile(r"^apps/[^/]+/manifest$"), "app.configure"),
    Rule(
        "POST",
        re.compile(r"^apps/[^/]+/(cloud|services|install|discard)$"),
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
}


def rule_for(method: str, path: str) -> Optional[Rule]:
    return next(
        (r for r in RULES if r.method == method and r.pattern.match(path)), None
    )


WORKSPACE_ROOTS = {"apps", "matrix", "plugins", "version", "gitflow"}
