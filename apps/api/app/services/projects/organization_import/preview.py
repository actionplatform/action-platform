"""What an import would do, before it runs: every repository, project, team and person with its state on the platform."""

from typing import Any, Callable

from action_platform.core.exception import ProviderError
from app.core.shared.ids import slugify
from app.services.projects.organization_import.step import ImportStep


class ImportPreview(ImportStep):
    def run(self, login: str) -> dict[str, Any]:
        self.problems: list[str] = []
        repositories = self._read("repositories", login, self.host.repositories)
        projects = self._read("projects", login, self.host.projects)
        teams = self._read("teams", login, self.host.teams)
        people = self._read("people", login, self.host.people)

        return {
            "organization": login,
            "host_kind": self.host.kind,
            "repositories": self._repositories(repositories),
            "projects": self._projects(projects),
            "teams": self._teams(teams),
            "people": self._people(people),
            "problems": self.problems,
            "limits": list(self.host.limits),
        }

    def _read(
        self, what: str, login: str, fetch: Callable[[str], list[dict]]
    ) -> list[dict]:
        try:
            return fetch(login)
        except ProviderError as e:
            hint = self.host.hint(what, login)
            self.problems.append(f"{what}: {e}")

            if hint and hint not in self.problems:
                self.problems.append(hint)

            return []

    def _repositories(self, rows: list[dict]) -> list[dict]:
        known = self.ctx.known_repositories()

        return [{**r, "imported_as": known.get(r["full_name"].lower())} for r in rows]

    def _projects(self, rows: list[dict]) -> list[dict]:
        return [
            {**p, "exists": self.ctx.project_named(p["title"]) is not None}
            for p in rows
        ]

    def _teams(self, rows: list[dict]) -> list[dict]:
        slugs = {t.slug for t in self.writes.teams_of(self.organization_id)}

        return [
            {**t, "exists": t["slug"] in slugs or slugify(t["name"]) in slugs}
            for t in rows
        ]

    def _people(self, rows: list[dict]) -> list[dict]:
        users = self.ctx.users_by_email([p["email"] for p in rows if p["email"]])
        members = self.ctx.member_ids()
        pending = self.ctx.pending_invitations(self.host.kind)
        can_prove = self.ctx.can_prove_login(self.host.kind)

        return [
            {
                **p,
                "role": p.get("role") or "member",
                "status": self._status(
                    p, users.get(p["email"] or ""), members, pending, can_prove
                ),
            }
            for p in rows
        ]

    @staticmethod
    def _status(
        person: dict, user, members: set[str], pending: dict, can_prove: bool
    ) -> str:
        if user and user.id in members:
            return "member"

        if user:
            return "user"

        if (person["email"] and person["email"] in pending) or (
            f"@{person['login'].lower()}" in pending
        ):
            return "invited"

        if person["email"]:
            return "invitable"

        if can_prove:
            return "invitable_login"

        return "no_email"
