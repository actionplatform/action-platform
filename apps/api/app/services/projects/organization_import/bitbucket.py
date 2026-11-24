"""What a Bitbucket Cloud token sees: workspaces, their projects and repositories, and members."""

import re
from typing import Any
from urllib.parse import quote

from action_platform.core.exception import ProviderError
from app.core.abc import HostDirectory
from app.core.shared.credentials import Credentials
from app.core.shared.http import BasicAuth, http

API = "https://api.bitbucket.org/2.0"


class BitbucketDirectory(HostDirectory):
    kind = "bitbucket"
    label = "Bitbucket"
    limits = (
        "Bitbucket never shows a member's email: people are invited by nickname and join only with the Bitbucket account (uuid) listed in the workspace.",
        "Bitbucket Cloud's API does not list a workspace's user groups, so no teams are offered; create them under Organization › Teams.",
    )

    def __init__(self, creds: Credentials) -> None:
        self.headers = {
            "authorization": BasicAuth.header(creds.username, creds.token)
            if creds.username
            else f"Bearer {creds.token}"
        }
        self._me: dict[str, Any] | None = None
        self._repositories: dict[str, list[dict[str, Any]]] = {}

    def me(self) -> dict[str, Any]:
        if self._me is None:
            self._me = http.get_json(f"{API}/user", self.headers)

        return self._me

    def organizations(self) -> list[dict[str, Any]]:
        """Every workspace the token can see, the personal one first."""
        mine = {(self.me().get(k) or "").lower() for k in ("username", "nickname")} - {
            ""
        }
        rows = []

        for p in http.get_values(
            f"{API}/user/permissions/workspaces?pagelen=100", self.headers
        ):
            w = p.get("workspace") or {}

            if not w.get("slug"):
                continue

            rows.append(
                {
                    "login": w["slug"],
                    "name": w.get("name") or w["slug"],
                    "kind": "user" if w["slug"].lower() in mine else "org",
                    "avatar": ((w.get("links") or {}).get("avatar") or {}).get("href"),
                }
            )

        return sorted(rows, key=lambda r: r["kind"] != "user")

    def repositories(self, login: str) -> list[dict[str, Any]]:
        if login not in self._repositories:
            self._repositories[login] = [
                self._repository(r)
                for r in http.get_values(
                    f"{API}/repositories/{quote(login)}?pagelen=100", self.headers
                )
            ]

        return self._repositories[login]

    def projects(self, login: str) -> list[dict[str, Any]]:
        """Bitbucket projects of the workspace, each with its repositories."""
        repositories = self.repositories(login)

        return [
            {
                "number": p["key"],
                "title": p.get("name") or p["key"],
                "description": p.get("description") or None,
                "closed": False,
                "url": ((p.get("links") or {}).get("html") or {}).get("href"),
                "repositories": [
                    r["full_name"] for r in repositories if r["project"] == p["key"]
                ],
            }
            for p in http.get_values(
                f"{API}/workspaces/{quote(login)}/projects?pagelen=100", self.headers
            )
        ]

    def teams(self, login: str) -> list[dict[str, Any]]:
        return []

    def people(self, login: str) -> list[dict[str, Any]]:
        try:
            owners = {
                (p.get("user") or {}).get("uuid")
                for p in http.get_values(
                    f"{API}/workspaces/{quote(login)}/permissions?pagelen=100",
                    self.headers,
                )
                if p.get("permission") == "owner"
            }
        except ProviderError:
            owners = set()

        rows = []

        for m in http.get_values(
            f"{API}/workspaces/{quote(login)}/members?pagelen=100", self.headers
        ):
            user = m.get("user") or {}
            nickname = user.get("nickname") or user.get("username")

            if not nickname or user.get("type") == "team":
                continue

            rows.append(
                {
                    "login": nickname,
                    "user_id": user.get("uuid"),
                    "name": user.get("display_name") or nickname,
                    "email": None,
                    "avatar": ((user.get("links") or {}).get("avatar") or {}).get(
                        "href"
                    ),
                    "role": "org_admin" if user.get("uuid") in owners else "member",
                }
            )

        return rows

    @staticmethod
    def _repository(r: dict[str, Any]) -> dict[str, Any]:
        clone = next(
            (
                c["href"]
                for c in (r.get("links") or {}).get("clone") or []
                if c.get("name") == "https"
            ),
            f"https://bitbucket.org/{r['full_name']}.git",
        )

        return {
            "full_name": r["full_name"],
            "name": r.get("slug") or r["full_name"].split("/")[-1],
            "description": r.get("description") or None,
            "private": bool(r.get("is_private")),
            "archived": False,
            "fork": bool(r.get("parent")),
            "language": r.get("language") or None,
            "default_branch": (r.get("mainbranch") or {}).get("name") or "main",
            "url": re.sub(r"//[^@/]+@", "//", clone),
            "pushed_at": r.get("updated_on"),
            "project": (r.get("project") or {}).get("key"),
        }
