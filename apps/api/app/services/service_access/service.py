"""The organization as the access engine sees it — members with role and teams from the database, the mapping kept in the plugin options table under `access` — GitHub's provider from the organization's GitHub connection, which wins over any plugin's, and the providers of every bundled plugin the organization's options configure."""

from __future__ import annotations

from typing import Any, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.core.service_access import (
    Access,
    Audit,
    Directory,
    Mapping,
    Person,
    Plan,
    Who,
)
from action_platform.plugins import registry
from action_platform.providers.access.github import BranchProtection, OrgSettings
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.errors import Forbidden, Invalid
from app.repositories.organization import OrganizationRepository
from app.services.integrations.plugins.options import DbOptions
from app.services.service_access.github import KIND as GITHUB, GitHubConnection

MAPPING = ("access", "mapping")


class OrganizationDirectory(Directory):
    def __init__(
        self,
        repo: OrganizationRepository,
        store: DbOptions,
        organization_id: str,
        caller_id: str,
    ) -> None:
        self.repo = repo
        self.store = store
        self.organization_id = organization_id
        self.caller_id = caller_id

    def people(self) -> list[Person]:
        teams: dict[str, list[str]] = {}

        for team in self.repo.teams_of(self.organization_id):
            for user in self.repo.team_members_of(team.id):
                teams.setdefault(user.id, []).append(team.slug)

        return [
            Person(
                email=(user.email or "").lower(),
                user_id=user.id,
                name=user.name or "",
                role=member.role,
                teams=tuple(sorted(teams.get(user.id, []))),
            )
            for member, user in self.repo.members_of(self.organization_id)
        ]

    def load(self) -> Mapping:
        return Mapping.of(self.store.get(MAPPING[1]))

    def save(self, mapping: Mapping) -> None:
        self.store.set(MAPPING[1], mapping.as_dict())

    def check_remove(self, person: Person) -> None:
        if self.repo.role_in(person.user_id, self.organization_id) != "owner":
            return

        if self.repo.role_in(self.caller_id, self.organization_id) != "owner":
            raise Forbidden("only an owner may remove an owner")

        owners = [
            m
            for m, _ in self.repo.members_of(self.organization_id)
            if m.role == "owner"
        ]

        if len(owners) <= 1:
            raise Invalid("the organization needs at least one owner")

    def remove(self, person: Person) -> None:
        self.check_remove(person)
        self.repo.remove_member(self.organization_id, person.user_id)


class ServiceAccess:
    def __init__(
        self,
        database: Database,
        sealer: Optional[Sealer],
        repo: OrganizationRepository,
        organization_id: str,
        caller_id: str,
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.repo = repo
        self.organization_id = organization_id
        self.caller_id = caller_id

    def engine(self) -> Access:
        providers, errors = registry.installed().access_providers(self._options)
        providers.pop(GITHUB, None)
        errors.pop(GITHUB, None)

        try:
            github = GitHubConnection(
                self.database, self.sealer, self.organization_id
            ).provider()
        except ActionPlatformError as e:
            errors[GITHUB] = str(e)
        else:
            if github is not None:
                providers[GITHUB] = github

        if not providers and not errors:
            raise Invalid(
                "no service to manage: connect GitHub under Settings → Git, or configure a plugin that brings access under Plugins"
            )

        directory = OrganizationDirectory(
            self.repo,
            self._options(MAPPING[0]),
            self.organization_id,
            self.caller_id,
        )

        return Access(directory, providers, errors)

    def audit(self, service: Optional[str] = None) -> Audit:
        return self.engine().audit(service)

    def who(self, person: Optional[str] = None, service: Optional[str] = None) -> Who:
        return self.engine().who(person, service)

    def sync(self, body: Any) -> Plan:
        return self.engine().sync(body.service, body.apply, body.reimport, body.links)

    def grant(self, body: Any) -> Plan:
        return self.engine().grant(
            body.person,
            body.service,
            body.resource,
            body.level,
            body.account,
            body.apply,
        )

    def revoke(self, body: Any) -> Plan:
        return self.engine().revoke(
            body.person, body.service, body.resource, body.apply
        )

    def offboard(self, body: Any) -> Plan:
        return self.engine().offboard(
            body.person, body.apply, body.remove_from_platform
        )

    def github_branch_protection(self, repo: Optional[str] = None) -> BranchProtection:
        return self._github().branch_protection(repo)

    def github_repo_settings(self, repo: Optional[str] = None) -> OrgSettings:
        return self._github().repo_settings(repo)

    def _github(self) -> GitHubConnection:
        return GitHubConnection(self.database, self.sealer, self.organization_id)

    def _options(self, slug: str) -> DbOptions:
        return DbOptions(self.database, slug, self.organization_id, self.sealer)
