"""What a GitLab token sees: groups, their subgroups and projects, and members with their access level — gitlab.com or a self-hosted instance."""

import re
from typing import Any
from urllib.parse import quote

from action_platform.core.exception import ProviderError
from app.core.abc import HostDirectory
from app.core.shared.credentials import Credentials
from app.core.shared.http import http

PEOPLE_LOOKUP_LIMIT = 200
OWNER = 50
MAINTAINER = 40


class GitlabDirectory(HostDirectory):
    kind = "gitlab"
    label = "GitLab"
    limits = (
        "GitLab shows a person's email only when they made it public on their profile.",
    )

    def __init__(self, creds: Credentials) -> None:
        web = re.sub(r"/api/v4$", "", (creds.base_url or "").rstrip("/"))
        self.api = f"{web or 'https://gitlab.com'}/api/v4"
        self.headers = {"authorization": f"Bearer {creds.token}"}
        self._me: dict[str, Any] | None = None
        self._groups: dict[str, dict[str, Any]] = {}
        self._repositories: dict[str, list[dict[str, Any]]] = {}

    def me(self) -> dict[str, Any]:
        if self._me is None:
            self._me = http.get_json(f"{self.api}/user", self.headers)

        return self._me

    def is_user(self, login: str) -> bool:
        return self.me()["username"].lower() == login.lower()

    def organizations(self) -> list[dict[str, Any]]:
        """The account itself, then every top-level group the token is a member of."""
        me = self.me()
        rows = [
            {
                "login": me["username"],
                "name": me.get("name") or me["username"],
                "kind": "user",
                "avatar": me.get("avatar_url"),
            }
        ]

        for g in http.get_pages(
            f"{self.api}/groups?min_access_level=10&top_level_only=true&order_by=path",
            self.headers,
        ):
            rows.append(
                {
                    "login": g["full_path"],
                    "name": g.get("full_name") or g["full_path"],
                    "kind": "org",
                    "avatar": g.get("avatar_url"),
                }
            )

        return rows

    def repositories(self, login: str) -> list[dict[str, Any]]:
        if login in self._repositories:
            return self._repositories[login]

        url = (
            f"{self.api}/users/{self.me()['id']}/projects?owned=true"
            if self.is_user(login)
            else f"{self.api}/groups/{self._id(login)}/projects?include_subgroups=true&with_shared=false"
        )

        self._repositories[login] = [
            self._repository(p) for p in http.get_pages(url, self.headers)
        ]

        return self._repositories[login]

    def projects(self, login: str) -> list[dict[str, Any]]:
        """Subgroups of the group, each with the repositories directly in it."""
        if self.is_user(login):
            return []

        repositories = self.repositories(login)
        rows = []

        for sub in self._subgroups(login):
            prefix = f"{sub['full_path'].lower()}/"
            rows.append(
                {
                    "number": sub["id"],
                    "title": self._relative(login, sub),
                    "description": sub.get("description") or None,
                    "closed": False,
                    "url": sub.get("web_url"),
                    "repositories": [
                        r["full_name"]
                        for r in repositories
                        if r["full_name"].lower().startswith(prefix)
                        and "/" not in r["full_name"][len(prefix) :]
                    ],
                }
            )

        return rows

    def teams(self, login: str) -> list[dict[str, Any]]:
        """Subgroups as teams: their direct members and the repositories under them."""
        if self.is_user(login):
            return []

        repositories = self.repositories(login)
        rows = []

        for sub in self._subgroups(login):
            members = http.get_pages(
                f"{self.api}/groups/{sub['id']}/members", self.headers
            )
            prefix = f"{sub['full_path'].lower()}/"
            rows.append(
                {
                    "slug": self._relative(login, sub).replace("/", "-").lower(),
                    "name": self._relative(login, sub),
                    "description": sub.get("description") or None,
                    "members": [m["username"] for m in members],
                    "repositories": [
                        r["full_name"]
                        for r in repositories
                        if r["full_name"].lower().startswith(prefix)
                    ],
                }
            )

        return rows

    def people(self, login: str) -> list[dict[str, Any]]:
        if self.is_user(login):
            members = [{**self.me(), "access_level": OWNER}]
        else:
            members = http.get_pages(
                f"{self.api}/groups/{self._id(login)}/members/all", self.headers
            )

        rows = []

        for m in members[:PEOPLE_LOOKUP_LIMIT]:
            if m.get("state") not in (None, "active") or m.get("bot"):
                continue

            try:
                profile = http.get_json(f"{self.api}/users/{m['id']}", self.headers)
            except ProviderError:
                profile = {}

            email = profile.get("public_email") or profile.get("email") or ""
            rows.append(
                {
                    "login": m["username"],
                    "user_id": str(m["id"]),
                    "name": m.get("name") or m["username"],
                    "email": email.strip().lower() or None,
                    "avatar": m.get("avatar_url"),
                    "role": self._role(m.get("access_level") or 0),
                }
            )

        return rows

    @staticmethod
    def _role(level: int) -> str:
        if level >= OWNER:
            return "org_admin"

        if level >= MAINTAINER:
            return "team_maintainer"

        return "member"

    def _group(self, login: str) -> dict[str, Any]:
        if login not in self._groups:
            self._groups[login] = http.get_json(
                f"{self.api}/groups/{quote(login, safe='')}?with_projects=false",
                self.headers,
            )

        return self._groups[login]

    def _id(self, login: str) -> int:
        return self._group(login)["id"]

    def _subgroups(self, login: str) -> list[dict[str, Any]]:
        return http.get_pages(
            f"{self.api}/groups/{self._id(login)}/descendant_groups?order_by=path",
            self.headers,
        )

    @staticmethod
    def _relative(login: str, group: dict[str, Any]) -> str:
        return group["full_path"][len(login) + 1 :] or group["full_path"]

    @staticmethod
    def _repository(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "full_name": p["path_with_namespace"],
            "name": p["path"],
            "description": p.get("description") or None,
            "private": p.get("visibility") != "public",
            "archived": bool(p.get("archived")),
            "fork": bool(p.get("forked_from_project")),
            "language": None,
            "default_branch": p.get("default_branch") or "main",
            "url": p["http_url_to_repo"],
            "pushed_at": p.get("last_activity_at"),
        }
