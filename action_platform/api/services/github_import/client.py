"""What a GitHub token sees: organizations, repositories, teams and people."""

from typing import Any

from action_platform.abc import HostDirectory
from action_platform.api.services.shared.credentials import Credentials
from action_platform.api.services.shared.http import get_json, get_pages, post_json
from action_platform.core.exception import ProviderError

PEOPLE_LOOKUP_LIMIT = 200


def _headers(creds: Credentials) -> dict[str, str]:
    return {
        "authorization": f"Bearer {creds.token}",
        "x-github-api-version": "2022-11-28",
    }


def _api(creds: Credentials) -> str:
    return (creds.base_url or "").rstrip("/") or "https://api.github.com"


class GithubDirectory(HostDirectory):
    kind = "github"

    def __init__(self, creds: Credentials) -> None:
        if creds.kind != "github":
            raise ProviderError("only GitHub hosts can be imported for now")

        self.api = _api(creds)
        self.graphql = (
            "https://api.github.com/graphql"
            if self.api == "https://api.github.com"
            else self.api.removesuffix("/api/v3") + "/api/graphql"
        )
        self.headers = _headers(creds)
        self._me: dict[str, Any] | None = None

    def me(self) -> dict[str, Any]:
        if self._me is None:
            self._me = get_json(f"{self.api}/user", self.headers)

        return self._me

    def is_user(self, login: str) -> bool:
        return self.me()["login"].lower() == login.lower()

    def organizations(self) -> list[dict[str, Any]]:
        """The account itself, then every organization the token can see: memberships, `/user/orgs`, and the accounts a GitHub App is installed on."""
        me = self.me()
        rows = [
            {
                "login": me["login"],
                "name": me.get("name") or me["login"],
                "kind": "user",
                "avatar": me.get("avatar_url"),
            }
        ]
        seen = {me["login"].lower()}

        for org in self._organization_candidates():
            login = org.get("login")

            if not login or login.lower() in seen:
                continue

            seen.add(login.lower())
            rows.append(
                {
                    "login": login,
                    "name": org.get("description") or org.get("name") or login,
                    "kind": "org",
                    "avatar": org.get("avatar_url"),
                }
            )

        return rows

    def _organization_candidates(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []

        for url, pick in (
            (
                f"{self.api}/user/memberships/orgs?state=active",
                lambda m: m.get("organization") or {},
            ),
            (f"{self.api}/user/orgs", lambda o: o),
        ):
            try:
                found.extend(pick(row) for row in get_pages(url, self.headers))
            except ProviderError:
                continue

        try:
            installations = get_json(f"{self.api}/user/installations", self.headers)
        except ProviderError:
            installations = {}

        for i in (installations or {}).get("installations", []):
            account = i.get("account") or {}

            if account.get("type") == "Organization":
                found.append(account)

        return found

    def repositories(self, login: str) -> list[dict[str, Any]]:
        url = (
            f"{self.api}/user/repos?affiliation=owner"
            if self.is_user(login)
            else f"{self.api}/orgs/{login}/repos?type=all"
        )

        return [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "description": r.get("description"),
                "private": bool(r.get("private")),
                "archived": bool(r.get("archived")),
                "fork": bool(r.get("fork")),
                "language": r.get("language"),
                "default_branch": r.get("default_branch") or "main",
                "url": r["clone_url"],
                "pushed_at": r.get("pushed_at"),
            }
            for r in get_pages(url, self.headers)
            if r["full_name"].split("/")[0].lower() == login.lower()
        ]

    def teams(self, login: str) -> list[dict[str, Any]]:
        if self.is_user(login):
            return []

        rows = []

        for t in get_pages(f"{self.api}/orgs/{login}/teams", self.headers):
            slug = t["slug"]
            members = get_pages(
                f"{self.api}/orgs/{login}/teams/{slug}/members", self.headers
            )
            repos = get_pages(
                f"{self.api}/orgs/{login}/teams/{slug}/repos", self.headers
            )
            rows.append(
                {
                    "slug": slug,
                    "name": t["name"],
                    "description": t.get("description"),
                    "members": [m["login"] for m in members],
                    "repositories": [r["full_name"] for r in repos],
                }
            )

        return rows

    def projects(self, login: str) -> list[dict[str, Any]]:
        """GitHub Projects (v2) of the organization or user, with the repositories linked to each."""
        owner = "user" if self.is_user(login) else "organization"
        query = (
            "query($login: String!, $after: String) { %s(login: $login) { "
            "projectsV2(first: 50, after: $after) { nodes { number title shortDescription closed url "
            "repositories(first: 100) { nodes { nameWithOwner } } } "
            "pageInfo { hasNextPage endCursor } } } }" % owner
        )
        rows: list[dict[str, Any]] = []
        after = None

        while True:
            data = post_json(
                self.graphql,
                {"query": query, "variables": {"login": login, "after": after}},
                self.headers,
            )

            if data.get("errors"):
                raise ProviderError(
                    "; ".join(e.get("message", "") for e in data["errors"])
                )

            page = ((data.get("data") or {}).get(owner) or {}).get("projectsV2") or {}

            for p in page.get("nodes") or []:
                rows.append(
                    {
                        "number": p["number"],
                        "title": p["title"],
                        "description": p.get("shortDescription"),
                        "closed": bool(p.get("closed")),
                        "url": p.get("url"),
                        "repositories": [
                            r["nameWithOwner"]
                            for r in (p.get("repositories") or {}).get("nodes") or []
                        ],
                    }
                )

            info = page.get("pageInfo") or {}

            if not info.get("hasNextPage"):
                return rows

            after = info.get("endCursor")

    def people(self, login: str) -> list[dict[str, Any]]:
        if self.is_user(login):
            members = [self.me()]
        else:
            members = get_pages(f"{self.api}/orgs/{login}/members", self.headers)

        rows = []

        for m in members[:PEOPLE_LOOKUP_LIMIT]:
            try:
                profile = get_json(f"{self.api}/users/{m['login']}", self.headers)
            except ProviderError:
                profile = {}

            rows.append(
                {
                    "login": m["login"],
                    "name": profile.get("name") or m["login"],
                    "email": (profile.get("email") or "").strip().lower() or None,
                    "avatar": m.get("avatar_url"),
                }
            )

        return rows
