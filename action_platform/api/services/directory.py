import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from action_platform.api.auth.crypto import Sealer
from action_platform.api.db.models import (
    App,
    Invitation,
    Member,
    Organization,
    OrganizationSetting,
    Project,
    SourceHost,
    Team,
    TeamMember,
    TemplateSource,
    User,
)
from action_platform.api.db.models import OAuthApp as OAuthAppRow
from action_platform.api.services.http import basic, post_form
from action_platform.core.access import ROLES, normalize_role
from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings

DEFAULT_GIT_AUTHOR = ("Action Platform", "cloud@actionplatform.io")
REFRESH_MARGIN = timedelta(seconds=60)
INVITATION_TTL = timedelta(days=7)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GIT_URL = re.compile(r"^(https?://|git@|ssh://|file://)")
PROVIDERS = ("github", "gitlab", "bitbucket")
HOST_KINDS = ("github", "gitlab", "bitbucket", "generic")
HOST_LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "generic": "Git",
}


class DirectoryError(ActionPlatformError):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.strip().lower())).strip(
        "-"
    )


REPO_IN_URL = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$")


def repo_from_url(url: str) -> Optional[str]:
    match = REPO_IN_URL.search(url or "")

    return match.group(1) if match else None


def kind_of_url(url: str) -> Optional[str]:
    if "github.com" in url:
        return "github"

    if "gitlab" in url:
        return "gitlab"

    if "bitbucket.org" in url:
        return "bitbucket"

    return None


@dataclass(frozen=True)
class Credentials:
    kind: str
    token: str
    username: Optional[str]
    base_url: Optional[str]
    owner: Optional[str]

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "token": self.token,
            "username": self.username,
            "base_url": self.base_url,
            "owner": self.owner,
        }


@dataclass(frozen=True)
class OAuthApp:
    client_id: str
    client_secret: str
    base_url: Optional[str]
    slug: Optional[str] = None


def oauth_app_for(kind: str) -> Optional[OAuthApp]:
    prefix = kind.upper()
    client_id = settings.env(f"AP_{prefix}_CLIENT_ID") or settings.env(
        f"{prefix}_CLIENT_ID"
    )
    client_secret = settings.env(f"AP_{prefix}_CLIENT_SECRET") or settings.env(
        f"{prefix}_CLIENT_SECRET"
    )

    if not client_id or not client_secret:
        return None

    return OAuthApp(
        client_id,
        client_secret,
        settings.env(f"AP_{prefix}_BASE_URL") or settings.env(f"{prefix}_BASE_URL"),
    )


def refresh_oauth(
    app: Optional[OAuthApp], kind: str, refresh_token: str
) -> tuple[str, Optional[str], Optional[datetime]]:
    if app is None:
        raise DirectoryError(
            f"the {kind} token expired and no OAuth app is configured on the API to refresh it"
        )

    if kind == "gitlab":
        base = (app.base_url or "https://gitlab.com").rstrip("/")
        data = post_form(
            f"{base}/oauth/token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    elif kind == "bitbucket":
        data = post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {"grant_type": "refresh_token", "refresh_token": refresh_token},
            {"authorization": basic(app.client_id, app.client_secret)},
        )
    else:
        base = re.sub(
            r"/api/v3$", "", (app.base_url or "https://github.com").rstrip("/")
        )
        data = post_form(
            f"{base}/login/oauth/access_token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    access = data.get("access_token")

    if not isinstance(access, str) or not access:
        raise DirectoryError("no access token in the provider's response")

    expires_in = data.get("expires_in")
    expires_at = (
        now() + timedelta(seconds=int(expires_in))
        if isinstance(expires_in, (int, float))
        else None
    )
    refreshed = data.get("refresh_token")

    return access, refreshed if isinstance(refreshed, str) else None, expires_at


class DirectoryService:
    """Organizations, projects, apps, teams, members, source hosts and template sources — the data every surface shares."""

    def __init__(self, db: DbSession, sealer: Optional[Sealer] = None) -> None:
        self.db = db
        self.sealer = sealer

    def organizations_of(
        self, user_id: str
    ) -> list[tuple[Organization, Optional[str]]]:
        rows = self.db.execute(
            select(Organization, Member.role)
            .join(Member, Member.organization_id == Organization.id)
            .where(Member.user_id == user_id)
            .order_by(Organization.name)
        ).all()

        return [(organization, normalize_role(role)) for organization, role in rows]

    def organization(self, id_or_slug: str) -> Optional[Organization]:
        return self.db.scalar(
            select(Organization).where(
                (Organization.id == id_or_slug) | (Organization.slug == id_or_slug)
            )
        )

    def role_in(self, user_id: str, organization_id: str) -> Optional[str]:
        return normalize_role(
            self.db.scalar(
                select(Member.role).where(
                    Member.user_id == user_id, Member.organization_id == organization_id
                )
            )
        )

    def projects_of(
        self, organization_id: str, project_id: Optional[str] = None
    ) -> list[Project]:
        query = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.name)
        )

        if project_id:
            query = query.where(Project.id == project_id)

        return list(self.db.scalars(query))

    def project(self, organization_id: str, project_id: str) -> Optional[Project]:
        return self.db.scalar(
            select(Project).where(
                Project.id == project_id, Project.organization_id == organization_id
            )
        )

    def apps_of(self, project_id: str, app_id: Optional[str] = None) -> list[App]:
        query = (
            select(App)
            .where(App.project_id == project_id)
            .order_by(App.created_at.desc())
        )

        if app_id:
            query = query.where(App.id == app_id)

        return list(self.db.scalars(query))

    def app(self, project_id: str, app_id: str) -> Optional[App]:
        return self.db.scalar(
            select(App).where(App.id == app_id, App.project_id == project_id)
        )

    def app_by_registry_id(self, registry_id: str) -> Optional[tuple[App, Project]]:
        row = self.db.execute(
            select(App, Project)
            .join(Project, Project.id == App.project_id)
            .where(App.registry_id == registry_id)
        ).first()

        return (row[0], row[1]) if row else None

    def registry_ids_of(
        self,
        organization_id: str,
        project_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> set[str]:
        query = (
            select(App.registry_id)
            .join(Project, Project.id == App.project_id)
            .where(Project.organization_id == organization_id)
        )

        if project_id:
            query = query.where(App.project_id == project_id)

        if app_id:
            query = query.where(App.id == app_id)

        return set(self.db.scalars(query))

    def mark_synced(self, app: App) -> None:
        app.last_synced_at = now()
        self.db.flush()

    def team(self, organization_id: str, team_id: str) -> Optional[Team]:
        return self.db.scalar(
            select(Team).where(
                Team.id == team_id, Team.organization_id == organization_id
            )
        )

    def teams_of(self, organization_id: str) -> list[Team]:
        return list(
            self.db.scalars(
                select(Team)
                .where(Team.organization_id == organization_id)
                .order_by(Team.name)
            )
        )

    def team_members_of(self, team_id: str) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .join(TeamMember, TeamMember.user_id == User.id)
                .where(TeamMember.team_id == team_id)
                .order_by(User.name)
            )
        )

    def team_projects_of(self, team_id: str) -> list[Project]:
        return list(
            self.db.scalars(
                select(Project).where(Project.team_id == team_id).order_by(Project.name)
            )
        )

    def members_of(self, organization_id: str) -> list[tuple[Member, User]]:
        rows = self.db.execute(
            select(Member, User)
            .join(User, User.id == Member.user_id)
            .where(Member.organization_id == organization_id)
            .order_by(Member.created_at)
        ).all()

        return [(member, user) for member, user in rows]

    def create_project(
        self, organization_id: str, name: str, description: str = ""
    ) -> Project:
        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        project = Project(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            slug=slugify(name),
            description=description.strip() or None,
            created_at=now(),
        )
        self.db.add(project)
        self.db.flush()

        return project

    def create_team(
        self, organization_id: str, name: str, description: str = ""
    ) -> Team:
        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        slug = slugify(name)

        if self.db.scalar(
            select(Team.id).where(
                Team.organization_id == organization_id, Team.slug == slug
            )
        ):
            raise DirectoryError(f"a team named {name} already exists")

        team = Team(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            slug=slug,
            description=description.strip() or None,
            created_at=now(),
        )
        self.db.add(team)
        self.db.flush()

        return team

    def add_team_member(self, organization_id: str, team_id: str, user_id: str) -> None:
        if self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        if self.role_in(user_id, organization_id) is None:
            raise DirectoryError("not a member of the organization")

        if self.db.scalar(
            select(TeamMember.id).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        ):
            return

        self.db.add(
            TeamMember(id=new_id(), team_id=team_id, user_id=user_id, created_at=now())
        )
        self.db.flush()

    def assign_project_team(
        self, organization_id: str, project_id: str, team_id: Optional[str]
    ) -> None:
        project = self.project(organization_id, project_id)

        if project is None:
            raise DirectoryError("project not found")

        if team_id and self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        project.team_id = team_id or None
        self.db.flush()

    def set_member_role(self, organization_id: str, user_id: str, role: str) -> None:
        if role not in ROLES:
            raise DirectoryError(f"role must be one of {', '.join(ROLES)}")

        member = self.db.scalar(
            select(Member).where(
                Member.organization_id == organization_id, Member.user_id == user_id
            )
        )

        if member is None:
            raise DirectoryError("member not found")

        owners = (
            self.db.scalar(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.organization_id == organization_id, Member.role == "owner"
                )
            )
            or 0
        )

        if member.role == "owner" and role != "owner" and owners <= 1:
            raise DirectoryError("the organization needs at least one owner")

        member.role = role
        self.db.flush()

    def git_author_of(self, organization_id: str) -> tuple[str, str]:
        row = self.db.get(OrganizationSetting, organization_id)

        return (
            (row.git_author_name, row.git_author_email) if row else DEFAULT_GIT_AUTHOR
        )

    def hosts_of(self, organization_id: str) -> list[SourceHost]:
        return list(
            self.db.scalars(
                select(SourceHost)
                .where(SourceHost.organization_id == organization_id)
                .order_by(SourceHost.created_at)
            )
        )

    def host_id_for_url(self, organization_id: str, url: str) -> Optional[str]:
        kind = kind_of_url(url)

        if kind is None:
            return None

        return next(
            (h.id for h in self.hosts_of(organization_id) if h.kind == kind), None
        )

    def credentials_for(
        self, organization_id: str, host_id: Optional[str]
    ) -> Optional[Credentials]:
        if not host_id or self.sealer is None:
            return None

        host = self.db.scalar(
            select(SourceHost).where(
                SourceHost.id == host_id, SourceHost.organization_id == organization_id
            )
        )

        if host is None:
            return None

        token = self.sealer.open(host.token_encrypted)

        if (
            host.auth_kind == "oauth"
            and host.refresh_token_encrypted
            and host.expires_at
            and host.expires_at - now() < REFRESH_MARGIN
        ):
            token, refreshed, expires_at = refresh_oauth(
                self.oauth_app(host.kind),
                host.kind,
                self.sealer.open(host.refresh_token_encrypted),
            )
            host.token_encrypted = self.sealer.seal(token)

            if refreshed:
                host.refresh_token_encrypted = self.sealer.seal(refreshed)

            host.expires_at = expires_at
            self.db.flush()

        return Credentials(
            host.kind, token, host.username, host.base_url, host.default_owner
        )

    def oauth_app(self, provider: str) -> Optional[OAuthApp]:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None and self.sealer is not None:
            return OAuthApp(
                row.client_id,
                self.sealer.open(row.client_secret_encrypted),
                row.base_url,
                row.slug,
            )

        return oauth_app_for(provider)

    def oauth_apps(self) -> dict[str, Optional[OAuthApp]]:
        return {provider: self.oauth_app(provider) for provider in PROVIDERS}

    def template_sources_of(self, organization_id: str) -> list[TemplateSource]:
        return list(
            self.db.scalars(
                select(TemplateSource)
                .where(TemplateSource.organization_id == organization_id)
                .order_by(TemplateSource.created_at)
            )
        )

    def source_specs_of(self, organization_id: str) -> list[dict]:
        specs = []

        for row in self.template_sources_of(organization_id):
            credentials = self.credentials_for(organization_id, row.source_host_id)
            specs.append(
                {
                    "name": row.name,
                    "url": row.url,
                    "ref": row.ref,
                    "credentials": credentials.as_dict() if credentials else None,
                }
            )

        return specs

    def source_spec_by_name(
        self, organization_id: str, name: Optional[str]
    ) -> Optional[dict]:
        if not name or name == "official":
            return None

        spec = next(
            (s for s in self.source_specs_of(organization_id) if s["name"] == name),
            None,
        )

        if spec is None:
            raise DirectoryError(f"template source {name} not found")

        return spec


class DirectoryWrites(DirectoryService):
    """The writes the web app's pages used to do themselves: projects, apps, teams, members, invitations, hosts, template sources, settings."""

    def delete_project(self, organization_id: str, project_id: str) -> list[str]:
        project = self.project(organization_id, project_id)

        if project is None:
            raise DirectoryError("project not found")

        registry_ids = [a.registry_id for a in self.apps_of(project.id)]
        self.db.delete(project)
        self.db.flush()

        return registry_ids

    def create_app(
        self,
        project_id: str,
        registry_id: str,
        name: str,
        source_host_id: Optional[str],
    ) -> App:
        app = App(
            id=new_id(),
            project_id=project_id,
            registry_id=registry_id,
            name=name,
            source_host_id=source_host_id,
            created_at=now(),
        )
        self.db.add(app)
        self.db.flush()

        return app

    def delete_app(self, project_id: str, app_id: str) -> Optional[App]:
        app = self.app(project_id, app_id)

        if app is None:
            return None

        self.db.delete(app)
        self.db.flush()

        return app

    def set_app_host(self, app: App, source_host_id: Optional[str]) -> None:
        app.source_host_id = source_host_id
        self.db.flush()

    def update_team(
        self, organization_id: str, team_id: str, name: str, description: str
    ) -> Team:
        team = self.team(organization_id, team_id)

        if team is None:
            raise DirectoryError("team not found")

        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        team.name = name
        team.slug = slugify(name)
        team.description = description.strip() or None
        self.db.flush()

        return team

    def delete_team(self, organization_id: str, team_id: str) -> None:
        team = self.team(organization_id, team_id)

        if team is None:
            raise DirectoryError("team not found")

        for project in self.team_projects_of(team.id):
            project.team_id = None

        self.db.delete(team)
        self.db.flush()

    def remove_team_member(
        self, organization_id: str, team_id: str, user_id: str
    ) -> None:
        if self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        row = self.db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )

        if row is not None:
            self.db.delete(row)
            self.db.flush()

    def remove_member(self, organization_id: str, user_id: str) -> None:
        member = self.db.scalar(
            select(Member).where(
                Member.organization_id == organization_id, Member.user_id == user_id
            )
        )

        if member is None:
            raise DirectoryError("member not found")

        owners = (
            self.db.scalar(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.organization_id == organization_id, Member.role == "owner"
                )
            )
            or 0
        )

        if member.role == "owner" and owners <= 1:
            raise DirectoryError("the organization needs at least one owner")

        for team in self.teams_of(organization_id):
            self.remove_team_member(organization_id, team.id, user_id)

        self.db.delete(member)
        self.db.flush()

    def invitations_of(self, organization_id: str) -> list[tuple[Invitation, User]]:
        rows = self.db.execute(
            select(Invitation, User)
            .join(User, User.id == Invitation.inviter_id)
            .where(
                Invitation.organization_id == organization_id,
                Invitation.status == "pending",
                Invitation.expires_at > now(),
            )
            .order_by(Invitation.created_at)
        ).all()

        return [(invitation, user) for invitation, user in rows]

    def create_invitation(
        self, organization_id: str, inviter_id: str, email: str, role: str
    ) -> Invitation:
        email = email.strip().lower()

        if role not in ROLES:
            raise DirectoryError(f"role must be one of {', '.join(ROLES)}")

        if not EMAIL.match(email):
            raise DirectoryError("enter a valid email")

        already = self.db.scalar(
            select(Member.id)
            .join(User, User.id == Member.user_id)
            .where(Member.organization_id == organization_id, User.email == email)
        )

        if already:
            raise DirectoryError("already a member")

        for invitation, _ in self.invitations_of(organization_id):
            if invitation.email == email:
                return invitation

        moment = now()
        invitation = Invitation(
            id=new_id(),
            organization_id=organization_id,
            email=email,
            role=role,
            status="pending",
            expires_at=moment + INVITATION_TTL,
            created_at=moment,
            inviter_id=inviter_id,
        )
        self.db.add(invitation)
        self.db.flush()

        return invitation

    def cancel_invitation(self, organization_id: str, id: str) -> None:
        invitation = self.db.scalar(
            select(Invitation).where(
                Invitation.id == id, Invitation.organization_id == organization_id
            )
        )

        if invitation is not None:
            invitation.status = "canceled"
            self.db.flush()

    def invitation(self, id: str) -> Optional[tuple[Invitation, User, Organization]]:
        row = self.db.execute(
            select(Invitation, User, Organization)
            .join(User, User.id == Invitation.inviter_id)
            .join(Organization, Organization.id == Invitation.organization_id)
            .where(Invitation.id == id)
        ).first()

        return (row[0], row[1], row[2]) if row else None

    def accept_invitation(self, id: str, user: User) -> Organization:
        found = self.invitation(id)

        if found is None:
            raise DirectoryError("invitation not found")

        invitation, _, organization = found

        if invitation.status != "pending":
            raise DirectoryError(f"invitation {invitation.status}")

        if invitation.expires_at < now():
            raise DirectoryError("invitation expired")

        if invitation.email != user.email.lower():
            raise DirectoryError(f"this invitation is for {invitation.email}")

        if self.role_in(user.id, organization.id) is None:
            self.db.add(
                Member(
                    id=new_id(),
                    organization_id=organization.id,
                    user_id=user.id,
                    role=invitation.role or "developer",
                    created_at=now(),
                )
            )

        invitation.status = "accepted"
        self.db.flush()

        return organization

    def host(self, organization_id: str, host_id: str) -> Optional[SourceHost]:
        return self.db.scalar(
            select(SourceHost).where(
                SourceHost.id == host_id, SourceHost.organization_id == organization_id
            )
        )

    def add_host(
        self,
        organization_id: str,
        kind: str,
        name: str,
        token: str,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        default_owner: Optional[str] = None,
    ) -> SourceHost:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        if kind not in HOST_KINDS:
            raise DirectoryError("unknown host kind")

        if not token.strip():
            raise DirectoryError("token is required")

        host = SourceHost(
            id=new_id(),
            organization_id=organization_id,
            kind=kind,
            name=name.strip() or HOST_LABELS[kind],
            base_url=(base_url or "").strip() or None,
            username=(username or "").strip() or None,
            token_encrypted=self.sealer.seal(token.strip()),
            default_owner=(default_owner or "").strip() or None,
            auth_kind="token",
            created_at=now(),
        )
        self.db.add(host)
        self.db.flush()

        return host

    def connect_oauth_host(
        self,
        organization_id: str,
        provider: str,
        login: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        base_url: Optional[str],
        owner: Optional[str] = None,
    ) -> SourceHost:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        host = self.db.scalar(
            select(SourceHost).where(
                SourceHost.organization_id == organization_id,
                SourceHost.kind == provider,
                SourceHost.auth_kind == "oauth",
                SourceHost.login == login,
            )
        )

        if host is None:
            host = SourceHost(
                id=new_id(),
                organization_id=organization_id,
                kind=provider,
                name=f"{HOST_LABELS[provider]} · {login}",
                username="x-token-auth" if provider == "bitbucket" else None,
                default_owner=owner or login,
                auth_kind="oauth",
                login=login,
                token_encrypted="",
                created_at=now(),
            )
            self.db.add(host)
        elif owner:
            host.default_owner = owner

        host.token_encrypted = self.sealer.seal(access_token)
        host.refresh_token_encrypted = (
            self.sealer.seal(refresh_token) if refresh_token else None
        )
        host.expires_at = expires_at
        host.base_url = base_url
        self.db.flush()

        return host

    def remove_host(self, organization_id: str, host_id: str) -> None:
        host = self.host(organization_id, host_id)

        if host is not None:
            self.db.delete(host)
            self.db.flush()

    def remove_oauth_host(
        self, organization_id: str, provider: str, login: str
    ) -> None:
        for host in self.db.scalars(
            select(SourceHost).where(
                SourceHost.organization_id == organization_id,
                SourceHost.kind == provider,
                SourceHost.auth_kind == "oauth",
                SourceHost.login == login,
            )
        ):
            self.db.delete(host)

        self.db.flush()

    def update_host_token(self, organization_id: str, host_id: str, token: str) -> None:
        host = self.host(organization_id, host_id)

        if host is None:
            raise DirectoryError("host not found")

        if not token.strip():
            raise DirectoryError("token is required")

        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        host.token_encrypted = self.sealer.seal(token.strip())
        self.db.flush()

    def set_host_owner(self, organization_id: str, host_id: str, owner: str) -> None:
        host = self.host(organization_id, host_id)

        if host is None:
            raise DirectoryError("host not found")

        host.default_owner = owner.strip() or None
        self.db.flush()

    def set_git_author(
        self, organization_id: str, name: str, email: str
    ) -> tuple[str, str]:
        name = name.strip()
        email = email.strip().lower()

        if not name:
            raise DirectoryError("name is required")

        if not EMAIL.match(email):
            raise DirectoryError("enter a valid email")

        row = self.db.get(OrganizationSetting, organization_id)

        if row is None:
            row = OrganizationSetting(
                organization_id=organization_id,
                git_author_name=name,
                git_author_email=email,
            )
            self.db.add(row)
        else:
            row.git_author_name = name
            row.git_author_email = email

        row.updated_at = now()
        self.db.flush()

        return name, email

    def add_template_source(
        self, organization_id: str, name: str, url: str, ref: str
    ) -> TemplateSource:
        name = slugify(name)
        url = url.strip()
        ref = ref.strip() or "main"

        if not name:
            raise DirectoryError("name is required")

        if name == "official":
            raise DirectoryError("official is reserved")

        if not GIT_URL.match(url):
            raise DirectoryError("enter a git url")

        if self.db.scalar(
            select(TemplateSource.id).where(
                TemplateSource.organization_id == organization_id,
                TemplateSource.name == name,
            )
        ):
            raise DirectoryError(f"a source named {name} already exists")

        row = TemplateSource(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            url=url,
            ref=ref,
            source_host_id=self.host_id_for_url(organization_id, url),
            created_at=now(),
        )
        self.db.add(row)
        self.db.flush()

        return row

    def remove_template_source(self, organization_id: str, id: str) -> None:
        row = self.db.scalar(
            select(TemplateSource).where(
                TemplateSource.id == id,
                TemplateSource.organization_id == organization_id,
            )
        )

        if row is not None:
            self.db.delete(row)
            self.db.flush()

    def save_oauth_app(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        base_url: Optional[str],
        slug: Optional[str] = None,
    ) -> OAuthApp:
        if provider not in PROVIDERS:
            raise DirectoryError("unknown provider")

        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        client_id = client_id.strip()
        client_secret = client_secret.strip()

        if not client_id or not client_secret:
            raise DirectoryError("client id and secret are required")

        row = self.db.get(OAuthAppRow, provider) or OAuthAppRow(provider=provider)
        row.client_id = client_id
        row.client_secret_encrypted = self.sealer.seal(client_secret)
        row.base_url = (base_url or "").strip() or None
        row.slug = slug or row.slug
        row.updated_at = now()
        self.db.add(row)
        self.db.flush()

        return OAuthApp(client_id, client_secret, row.base_url, row.slug)

    def clear_oauth_app(self, provider: str) -> None:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None:
            self.db.delete(row)
            self.db.flush()
