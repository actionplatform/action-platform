"""A GitHub organization: membership and its role, team membership, repository permissions of people and of teams."""

from __future__ import annotations

from typing import Optional

from action_platform.core.service_access import (
    AccessError,
    AccessProvider,
    Grant,
    Http,
    Op,
)

from action_platform.providers.access.github.client import API_URL, client

ROLE_NAMES = {"read": "pull", "write": "push"}
TEAM = "team:"
SCOPES = ("admin:org", "repo")
READ_SCOPES = (("read:org", "write:org", "admin:org"), ("repo",))
PERMISSIONS = (("members", "write"), ("administration", "write"))
LEVELS = {"read": 1, "write": 2, "admin": 3}
LABELS = {
    "members": "Organization → Members",
    "administration": "Repository → Administration",
}


class GitHubProvider(AccessProvider):
    """Accounts are logins; a team's own repository permissions are grants of the account `team:<slug>`."""

    name = "github"
    levels = {
        "org": ("member", "admin"),
        "team": ("member", "maintainer"),
        "repo": ("pull", "triage", "push", "maintain", "admin"),
    }

    def __init__(
        self,
        org: str,
        token: str,
        url: str = API_URL,
        http: Optional[Http] = None,
        app: Optional[str] = None,
    ) -> None:
        self.org = org
        self.http = http or client(token, url)
        self.app = app
        self.checked: set[bool] = set()

    def check(self, write: bool = False) -> None:
        """Raise `AccessError` naming the scope or the GitHub App permission the token lacks to read (or, with `write`, to change) access, with where to grant it."""
        if write in self.checked:
            return

        res = self.http.send("GET", "user")

        if res.status >= 400:
            raise AccessError(
                f"github: the token was refused ({res.status}); reconnect GitHub under Settings → Git"
            )

        held = res.headers.get("x-oauth-scopes")

        if self.app and not (held or "").strip():
            self._installation(write)
        elif held is not None:
            self._scopes(held, write)

        self.checked.add(write)

    def _scopes(self, held: str, write: bool) -> None:
        granted = {s.strip() for s in held.split(",") if s.strip()}
        needed = [(s,) for s in SCOPES] if write else READ_SCOPES
        missing = [any_of[0] for any_of in needed if not granted & set(any_of)]

        if missing:
            raise AccessError(
                f"github: the token lacks the {', '.join(missing)} scope; reconnect GitHub under Settings → Git (connecting asks for it) or use a token that has it"
            )

    def _installation(self, write: bool) -> None:
        listing = self.http.call("GET", "user/installations", query={"per_page": 100})
        found = next(
            (
                i
                for i in (listing or {}).get("installations", [])
                if (i.get("account") or {}).get("login", "").lower() == self.org.lower()
            ),
            None,
        )

        if found is None:
            raise AccessError(
                f"github: the GitHub App {self.app} is not installed on {self.org}; install it: https://github.com/apps/{self.app}/installations/new"
            )

        held = found.get("permissions") or {}
        wanted = "write" if write else "read"
        missing = [
            f'{LABELS[name]} "{"Read and write" if write else "Read"}" (is {held.get(name, "none")})'
            for name, _ in PERMISSIONS
            if LEVELS.get(held.get(name, ""), 0) < LEVELS[wanted]
        ]

        if missing:
            raise AccessError(
                f"github: the GitHub App {self.app} lacks {'; '.join(missing)}. Add it in the app's settings ({self._app_settings()}), then accept the new permissions on the installation: https://github.com/organizations/{self.org}/settings/installations/{found.get('id')}"
            )

    def _app_settings(self) -> str:
        res = self.http.send("GET", f"apps/{self.app}")
        owner = (res.data or {}).get("owner") or {} if res.status < 400 else {}

        if owner.get("type") == "Organization":
            return f"https://github.com/organizations/{owner['login']}/settings/apps/{self.app}/permissions"

        return f"https://github.com/settings/apps/{self.app}/permissions"

    def read(self) -> list[Grant]:
        self.check()
        grants: list[Grant] = []
        org = self.org

        for role in ("admin", "member"):
            for m in self.http.pages(
                f"orgs/{org}/members", {"role": role, "per_page": 100}
            ):
                grants.append(Grant("github", m["login"], "org", role))

        for inv in self.http.pages(f"orgs/{org}/invitations", {"per_page": 100}):
            if inv.get("login"):
                level = "admin" if inv.get("role") == "admin" else "member"
                grants.append(Grant("github", inv["login"], "org", level))

        for team in self.http.pages(f"orgs/{org}/teams", {"per_page": 100}):
            slug = team["slug"]

            for role in ("maintainer", "member"):
                for m in self.http.pages(
                    f"orgs/{org}/teams/{slug}/members", {"role": role, "per_page": 100}
                ):
                    grants.append(Grant("github", m["login"], f"team/{slug}", role))

            for repo in self.http.pages(
                f"orgs/{org}/teams/{slug}/repos", {"per_page": 100}
            ):
                grants.append(
                    Grant("github", TEAM + slug, f"repo/{repo['name']}", _level(repo))
                )

        for repo in self.http.pages(
            f"orgs/{org}/repos", {"type": "all", "per_page": 100}
        ):
            name = repo["name"]

            for c in self.http.pages(
                f"repos/{org}/{name}/collaborators",
                {"affiliation": "direct", "per_page": 100},
            ):
                grants.append(Grant("github", c["login"], f"repo/{name}", _level(c)))

            for inv in self.http.pages(
                f"repos/{org}/{name}/invitations", {"per_page": 100}
            ):
                if inv.get("invitee"):
                    level = ROLE_NAMES.get(
                        inv.get("permissions", ""), inv.get("permissions", "pull")
                    )
                    grants.append(
                        Grant("github", inv["invitee"]["login"], f"repo/{name}", level)
                    )

        return self.strongest(grants)

    def apply(self, op: Op) -> None:
        self.check(write=True)
        g, org = op.grant, self.org
        kind, _, target = g.resource.partition("/")
        removing = op.action == "remove"

        if kind == "org":
            if removing:
                self.http.call("DELETE", f"orgs/{org}/memberships/{g.account}")
            else:
                self.http.call(
                    "PUT", f"orgs/{org}/memberships/{g.account}", {"role": g.level}
                )
        elif kind == "team":
            if removing:
                self.http.call(
                    "DELETE", f"orgs/{org}/teams/{target}/memberships/{g.account}"
                )
            else:
                self._team(target)
                self.http.call(
                    "PUT",
                    f"orgs/{org}/teams/{target}/memberships/{g.account}",
                    {"role": g.level},
                )
        elif kind == "repo" and g.account.startswith(TEAM):
            slug = g.account[len(TEAM) :]

            if removing:
                self.http.call(
                    "DELETE", f"orgs/{org}/teams/{slug}/repos/{org}/{target}"
                )
            else:
                self._team(slug)
                self.http.call(
                    "PUT",
                    f"orgs/{org}/teams/{slug}/repos/{org}/{target}",
                    {"permission": g.level},
                )
        elif kind == "repo":
            if removing:
                self.http.call(
                    "DELETE", f"repos/{org}/{target}/collaborators/{g.account}"
                )
            else:
                self.http.call(
                    "PUT",
                    f"repos/{org}/{target}/collaborators/{g.account}",
                    {"permission": g.level},
                )
        else:
            raise AccessError(f"github: cannot apply {g.resource}")

    def companions(self, resource: str) -> list[tuple[str, str]]:
        return [("org", "member")] if self.kind(resource) == "team" else []

    def expand(self, grants: set[Grant]) -> set[Grant]:
        members = {g.account.lower() for g in grants if g.resource == "org"}
        joining = {
            g.account
            for g in grants
            if self.kind(g.resource) == "team" and g.account.lower() not in members
        }

        return grants | {Grant("github", a, "org", "member") for a in joining}

    def guard(self, ops: list[Op], live: list[Grant]) -> dict[Op, str]:
        admins = {
            g.account.lower()
            for g in live
            if g.resource == "org" and g.level == "admin"
        }
        losing = {
            op.grant.account.lower()
            for op in ops
            if op.grant.resource == "org"
            and op.grant.account.lower() in admins
            and (op.action == "remove" or op.grant.level != "admin")
        }

        if admins and losing >= admins:
            return {
                op: f"github: {op.grant.account} is the last organization admin of {self.org}"
                for op in ops
                if op.grant.resource == "org" and op.grant.account.lower() in losing
            }

        return {}

    def _team(self, slug: str) -> None:
        res = self.http.send("GET", f"orgs/{self.org}/teams/{slug}")

        if res.status == 404:
            self.http.call(
                "POST", f"orgs/{self.org}/teams", {"name": slug, "privacy": "closed"}
            )
        elif res.status >= 400:
            raise AccessError(f"github: team {slug} answered {res.status}")


def _level(row: dict) -> str:
    role = row.get("role_name")

    if role:
        return ROLE_NAMES.get(role, role)

    perms = row.get("permissions") or {}

    for level in ("admin", "maintain", "push", "triage", "pull"):
        if perms.get(level):
            return level

    return "pull"
