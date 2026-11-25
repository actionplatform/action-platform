"""GitHub in memory. It answers only the routes and fields the REST API sends, and keeps state, so a change shows up on the next read."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Optional

from action_platform.core.service_access import Http, Response


class FakeHttp(Http):
    def __init__(self, service: str, base: str) -> None:
        super().__init__(service, base, {})
        self.calls: list[tuple[str, str, Any]] = []

    def send(self, method, path, body=None, query=None, form=None) -> Response:
        url = urllib.parse.urlsplit(self.url(path, query))
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        route = urllib.parse.unquote(url.path).strip("/")
        sent = json.loads(json.dumps(body)) if body is not None else None
        self.calls.append((method, route, sent))

        return self.handle(method, route, q, sent)

    def writes(self) -> list[tuple[str, str, Any]]:
        return [c for c in self.calls if c[0] != "GET"]

    def handle(self, method: str, route: str, q: dict, body: Any) -> Response:
        raise NotImplementedError


def _paged(items: list, q: dict, size: Optional[int], url: str) -> Response:
    if size is None:
        return Response(200, items)

    start = int(q.get("cursor", "0"))
    headers = {}

    if start + size < len(items):
        nxt = f"{url}?{urllib.parse.urlencode({**q, 'cursor': start + size})}"
        last = f"{url}?{urllib.parse.urlencode({**q, 'cursor': len(items) - 1})}"
        headers["link"] = f'<{nxt}>; rel="next", <{last}>; rel="last"'

    return Response(200, items[start : start + size], headers)


class FakeGitHub(FakeHttp):
    def __init__(self, page: Optional[int] = None) -> None:
        super().__init__("github", "https://api.github.com")
        self.page = page
        self.members: dict[str, str] = {}
        self.invited: dict[str, str] = {}
        self.teams: dict[str, dict] = {}
        self.repos: dict[str, dict[str, str]] = {}
        self.documents: dict[str, dict] = {}
        self.protection: dict[str, Any] = {}
        self.rules: dict[str, list] = {}
        self.alerts: dict[str, bool] = {}
        self.denied: set[str] = set()
        self.scopes: Optional[str] = "admin:org, repo"
        self.installations: list[dict] = []
        self.app_owner: dict = {"login": "ana", "type": "User"}

    def repo(self, name: str, **fields: Any) -> dict:
        self.repos.setdefault(name, {})
        self.documents[name] = {
            "name": name,
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "archived": False,
            "delete_branch_on_merge": False,
            "allow_auto_merge": False,
            "security_and_analysis": {
                "dependabot_security_updates": {"status": "disabled"},
                "secret_scanning": {"status": "disabled"},
                "secret_scanning_push_protection": {"status": "disabled"},
            },
            **fields,
        }

        return self.documents[name]

    def handle(self, method, route, q, body):
        p = route.split("/")
        perm_names = {"pull": "read", "push": "write"}
        url = self.url(route)

        if route == "user":
            headers = {} if self.scopes is None else {"x-oauth-scopes": self.scopes}
            return Response(200, {"login": "ana"}, headers)

        if route == "user/installations":
            return Response(
                200,
                {
                    "total_count": len(self.installations),
                    "installations": self.installations,
                },
            )

        if p[0] == "apps":
            return Response(200, {"slug": p[1], "owner": self.app_owner})

        if p[:3] == ["orgs", "acme", "members"] and method == "GET":
            return _paged(
                [{"login": u} for u, r in self.members.items() if r == q["role"]],
                q,
                self.page,
                url,
            )

        if p[:3] == ["orgs", "acme", "invitations"]:
            return Response(
                200,
                [
                    {"login": u, "role": "direct_member" if r == "member" else r}
                    for u, r in self.invited.items()
                ],
            )

        if p[:3] == ["orgs", "acme", "memberships"]:
            if method == "PUT":
                self.members[p[3]] = body["role"]
            else:
                self.members.pop(p[3], None)
            return Response(200, {})

        if route == "orgs/acme/teams" and method == "GET":
            return Response(200, [{"slug": s} for s in self.teams])

        if route == "orgs/acme/teams" and method == "POST":
            self.teams[body["name"]] = {"members": {}, "repos": {}}
            return Response(201, {"slug": body["name"]})

        if p[:2] == ["orgs", "acme"] and p[2] == "teams":
            team = self.teams.get(p[3])

            if team is None:
                return Response(404, {"message": "Not Found"})

            if len(p) == 4:
                return Response(200, {"slug": p[3]})

            if p[4] == "members":
                return Response(
                    200,
                    [
                        {"login": u}
                        for u, r in team["members"].items()
                        if r == q["role"]
                    ],
                )

            if p[4] == "memberships":
                if method == "PUT":
                    team["members"][p[5]] = body["role"]
                else:
                    team["members"].pop(p[5], None)
                return Response(200, {})

            if p[4] == "repos" and method == "GET":
                return Response(
                    200,
                    [
                        {"name": n, "role_name": perm_names.get(v, v)}
                        for n, v in team["repos"].items()
                    ],
                )

            if p[4] == "repos":
                if method == "PUT":
                    team["repos"][p[6]] = body["permission"]
                else:
                    team["repos"].pop(p[6], None)
                return Response(204, None)

        if route == "orgs/acme/repos":
            return _paged(
                [
                    {
                        "name": n,
                        "private": d["private"],
                        "visibility": d["visibility"],
                        "default_branch": d["default_branch"],
                        "archived": d["archived"],
                        "delete_branch_on_merge": None,
                    }
                    for n, d in self.documents.items()
                ],
                q,
                self.page,
                url,
            )

        if p[:2] == ["repos", "acme"] and len(p) == 3:
            doc = self.documents.get(p[2])

            if doc is None:
                return Response(404, {"message": "Not Found"})

            return Response(200, doc)

        if p[0] == "repos" and p[3] == "collaborators":
            repo = self.repos.get(p[2])

            if repo is None:
                return Response(404, {"message": "Not Found"})

            if method == "GET":
                return Response(
                    200,
                    [
                        {"login": u, "role_name": perm_names.get(v, v)}
                        for u, v in repo.items()
                    ],
                )

            if method == "PUT":
                repo[p[4]] = body["permission"]
            else:
                repo.pop(p[4], None)
            return Response(201, {})

        if p[0] == "repos" and p[3] == "invitations":
            return Response(200, [])

        if p[0] == "repos" and p[3] == "branches" and p[-1] == "protection":
            return self._guarded(
                p[2],
                lambda: self._protection(p[2]),
                "https://docs.github.com/rest/branches/branch-protection#get-branch-protection",
            )

        if p[0] == "repos" and p[3:5] == ["rules", "branches"]:
            return self._guarded(
                p[2],
                lambda: Response(200, self.rules.get(p[2], [])),
                "https://docs.github.com/rest/repos/rules#get-rules-for-a-branch",
            )

        if p[0] == "repos" and p[3] == "vulnerability-alerts":
            if self.alerts.get(p[2]):
                return Response(204, None)

            return Response(
                404,
                {
                    "message": "Vulnerability alerts are disabled.",
                    "documentation_url": "https://docs.github.com/rest/repos/repos#check-if-vulnerability-alerts-are-enabled-for-a-repository",
                    "status": "404",
                },
            )

        return Response(404, {"message": f"no route {method} {route}"})

    def _guarded(self, repo: str, answer, docs: str) -> Response:
        if repo in self.denied:
            return Response(
                403,
                {
                    "message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
                    "documentation_url": docs,
                    "status": "403",
                },
            )

        return answer()

    def _protection(self, repo: str) -> Response:
        if repo not in self.protection:
            return Response(
                404,
                {
                    "message": "Branch not protected",
                    "documentation_url": "https://docs.github.com/rest/branches/branch-protection#get-branch-protection",
                    "status": "404",
                },
            )

        return Response(200, self.protection[repo])
