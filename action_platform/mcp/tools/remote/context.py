"""Recognise the local checkout the agent works in as an app on the platform."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.flow.repository import Repository
from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, tool
from action_platform.mcp.tools.remote.common import repo_key
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def current_context(
        project: Annotated[
            Optional[str],
            Field(description="Local directory to recognise; default is the cwd"),
        ] = None,
    ) -> schemas.CurrentContext:
        """Recognise the local checkout the agent is working in: matches its git remote to an app on the platform and returns the app, its project, the organization and what the token may do there. Use before acting on "this project"."""
        root = Path(project).resolve() if project else Path.cwd()
        repo = Repository(root)
        remote_url = repo.remote_url() if repo.exists() else ""
        key = repo_key(remote_url)
        who = remote.whoami()
        match = next(
            (a for a in remote.apps() if key and repo_key(a.url) == key),
            None,
        )
        projects = remote.projects() if match else []
        owner = (
            next(
                (p for p in projects for a in p.apps if a.registry_id == match.id),
                None,
            )
            if match
            else None
        )

        return {
            "directory": str(root),
            "remote": remote_url or None,
            "branch": repo.branch if repo.exists() else None,
            "organization": who.organization,
            "project": {
                "id": owner.id,
                "name": owner.name,
                "team": owner.team.model_dump() if owner.team else None,
            }
            if owner
            else None,
            "app": match.model_dump() if match else None,
            "role": who.role_name,
            "scope": who.scope,
            "can": who.permissions,
            "hint": None
            if match
            else "this directory is not an app on the platform — add_app registers it",
        }
