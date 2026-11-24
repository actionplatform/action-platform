"""Teams → teams, with the members who are already in the organization, the invitees who join on accepting, and the projects of their repositories."""

from app.core.db.models import Project, Team
from app.core.shared.ids import slugify
from app.services.projects.organization_import.people import People
from app.services.projects.organization_import.step import ImportStep


class TeamImporter(ImportStep):
    def run(
        self,
        login: str,
        wanted: set[str],
        projects_by_repo: dict[str, Project],
        people: People,
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
            self._fill(team, remote["members"], people, members)

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
        people: People,
        members: set[str],
    ) -> None:
        in_team = {u.id for u in self.writes.team_members_of(team.id)}

        for member_login in logins:
            key = member_login.lower()
            user = people.users.get(key)

            if user is not None and user.id in members:
                if user.id not in in_team:
                    self.writes.add_team_member(self.organization_id, team.id, user.id)
                    in_team.add(user.id)

                continue

            invitation = people.invitations.get(key)

            if invitation is not None:
                self.writes.add_invitation_teams(invitation, [team.id])
                self.summary.wait(invitation.email or f"@{member_login}", team.name)

    def _assign(
        self, team: Team, repositories: list[str], projects_by_repo: dict[str, Project]
    ) -> None:
        for repo in repositories:
            project = projects_by_repo.get(repo.lower())

            if project is not None and project.team_id is None:
                self.writes.assign_project_team(
                    self.organization_id, project.id, team.id
                )
