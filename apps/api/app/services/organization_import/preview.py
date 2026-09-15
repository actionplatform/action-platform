"""What an import would do, before it runs: every repository, project, team and person with its state on the platform."""

from typing import Any, Callable

from app.services.directory import slugify
from app.services.organization_import.step import ImportStep
from action_platform.core.exception import ProviderError

MEMBERS_HINT = (
    "Teams and people need the GitHub App permission Organization › Members (read) — "
    "update it under the app's settings on GitHub and accept it on the organization — "
    "or a token with the read:org scope."
)


class ImportPreview(ImportStep):
    def run(self, login: str) -> dict[str, Any]:
        self.problems: list[str] = []
        repositories = self._read(
            "repositories",
            lambda: self.host.repositories(login),
            self._repositories_hint(login),
        )
        projects = self._read(
            "projects",
            lambda: self.host.projects(login),
            "GitHub Projects need the GitHub App permission Organization › Projects (read) or a token with the read:project scope.",
        )
        teams = self._read("teams", lambda: self.host.teams(login), None)
        people = self._read("people", lambda: self.host.people(login), None)

        if any(p.startswith(("teams:", "people:")) for p in self.problems):
            self.problems.append(MEMBERS_HINT)

        return {
            "organization": login,
            "repositories": self._repositories(repositories),
            "projects": self._projects(projects),
            "teams": self._teams(teams),
            "people": self._people(people),
            "problems": self.problems,
        }

    def _read(
        self, what: str, fetch: Callable[[], list[dict]], hint: str | None
    ) -> list[dict]:
        try:
            return fetch()
        except ProviderError as e:
            self.problems.append(f"{what}: {e}" + (f". {hint}" if hint else ""))

            return []

    @staticmethod
    def _repositories_hint(login: str) -> str:
        return (
            f"The GitHub App must be installed on {login} with access to its repositories "
            "(Install the app on GitHub, pick the organization, all repositories); an OAuth token needs the repo scope."
        )

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
        pending = {i.email for i, _ in self.writes.invitations_of(self.organization_id)}

        return [
            {
                **p,
                "status": self._status(
                    p, users.get(p["email"] or ""), members, pending
                ),
            }
            for p in rows
        ]

    @staticmethod
    def _status(person: dict, user, members: set[str], pending: set[str]) -> str:
        if user and user.id in members:
            return "member"

        if user:
            return "user"

        if person["email"] in pending:
            return "invited"

        if person["email"]:
            return "invitable"

        return "no_email"
