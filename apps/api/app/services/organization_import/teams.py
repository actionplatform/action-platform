"""Teams → teams, with the members who are already in the organization and the projects of their repositories."""

from app.core.db.models import Project, Team, User
from app.services.directory import slugify
from app.services.organization_import.step import ImportStep


class TeamImporter(ImportStep):
    def run(
        self,
        login: str,
        wanted: set[str],
        projects_by_repo: dict[str, Project],
        user_by_login: dict[str, User],
    ) -> None:
        if not wanted:
            return

        existing = {t.slug: t for t in self.writes.teams_of(self.organization_id)}
        members = self.ctx.member_ids()
        shared = len({p.id for p in projects_by_repo.values()}) < len(projects_by_repo)

        for remote in self.host.teams(login):
            if remote["slug"].lower() not in wanted:
                continue

            team = self._team_for(remote, existing)
            self._fill(team, remote["members"], user_by_login, members)

            if not shared:
                self._assign(team, remote["repositories"], projects_by_repo)

    def _team_for(self, remote: dict, existing: dict[str, Team]) -> Team:
        team = existing.get(remote["slug"]) or existing.get(slugify(remote["name"]))

        if team is not None:
            self.summary.skip(f"team {remote['name']}", "already exists, updated")

            return team

        team = self.writes.create_team(
            self.organization_id, remote["name"], remote.get("description") or ""
        )
        self.summary.teams.append(team.name)

        return team

    def _fill(
        self,
        team: Team,
        logins: list[str],
        user_by_login: dict[str, User],
        members: set[str],
    ) -> None:
        in_team = {u.id for u in self.writes.team_members_of(team.id)}

        for member_login in logins:
            user = user_by_login.get(member_login.lower())

            if user is None or user.id not in members or user.id in in_team:
                continue

            self.writes.add_team_member(self.organization_id, team.id, user.id)
            in_team.add(user.id)

    def _assign(
        self, team: Team, repositories: list[str], projects_by_repo: dict[str, Project]
    ) -> None:
        for repo in repositories:
            project = projects_by_repo.get(repo.lower())

            if project is not None and project.team_id is None:
                self.writes.assign_project_team(
                    self.organization_id, project.id, team.id
                )
