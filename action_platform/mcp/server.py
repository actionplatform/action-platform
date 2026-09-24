"""Builds the MCP server and runs it over the chosen transport."""

from __future__ import annotations

import argparse
from typing import Optional

from mcp.server.mcpserver import MCPServer

from action_platform import __version__
from action_platform.bootstrap import bootstrap
from action_platform.mcp import annotations, prompts
from action_platform.mcp.tools import remote as remote_tools
from action_platform.remote.client import Remote
from action_platform.mcp.tools import flow, lifecycle, matrix, project
from action_platform.plugins import registry

INSTRUCTIONS = """Scaffold, deploy and operate projects on the Action Platform.

Start with list_matrix to learn the project types, stacks, templates,
clouds and services that exist; pass `source` (url[@ref]) to read a custom
templates repository instead of the official one. init_project generates a
new project; install_platform brings an existing repository in. Both work
locally; nothing reaches a remote host until push_project, which creates a
repository visible to others — confirm with the user before calling it.

Every project follows git-flow: work happens on <kind>/<code> branches
started with start_branch, never directly on main or develop. Finish with
propose_pull_request (preview) and open_pull_request (on approval);
gitflow_rules explains the rules when in doubt.

release and deploy default to dry runs: show the user what would happen,
then call again with dry_run=false. rollback changes what is live; ask first."""

RULES = """
Rules, whatever the transport:
- Git-flow always: never commit on main, master or develop; every change
  starts on a <kind>/<code>[-slug] branch from start_branch, and a pull
  request is opened only after gitflow_audit passes and the user approved
  the preview from propose_pull_request. Commit messages follow Conventional
  Commits; one commit per concern.
- The platform is reached only through these tools. Never call its HTTP
  API, its web app or the code host's API directly (no curl, fetch, gh api
  or hand-written requests), never read or forge its tokens and never run
  git push, gh pr create or a deploy command to bypass a tool: the tools
  carry the role, the scope and the audit trail; a direct call has none.
- Before an action that leaves the machine — push, pull request, release,
  deploy, rollback, removing an app or a project, deleting a repository —
  show what will happen and wait for an explicit yes. Dry runs first.
- When a tool refuses, report its reason and stop; do not look for another
  way around the permission.
"""

REMOTE_INSTRUCTIONS = """Operate apps on a hosted Action Platform.

These tools act on the platform the CLI is logged in to (`action-platform
login <server>`), not on files on this machine, and with the role the
account has in its organization (viewer, developer, deployer, admin, owner)
narrowed by the token's scope (read, write, release, admin, chosen at
login) and reach (one organization or all of them, optionally one project
or app — pass `organization` to organization-level tools when it spans
all): a
refused call names the missing permission or scope. Start with whoami (who,
where, what is allowed) or current_context (which platform app the local
checkout is); list_organizations, list_projects, list_teams and
list_members describe the organization; create_project, create_team,
add_team_member, assign_project_team and set_member_role change it when the
role and the token's scope allow. Every app is a repository the platform has cloned:
sync_app before auditing, editing or releasing so the clone is current.

Work follows git-flow: start_branch, then write_manifest / set_cloud /
add_service, then commit_changes (which can create the branch and open the
pull request in one call), or propose_pull_request + open_pull_request.
Protected branches refuse direct commits.

release and deploy default to dry runs: show the user what would happen,
then call again with dry_run=false. Stable versions come only from
main/master; pass `branch` to release from another branch. remove_app
deletes the platform's clone; ask first."""


def build(remote: Optional[str] = None) -> MCPServer:
    """Assemble the server. Local: tools call the core modules directly — same code path as the CLI.
    Remote: tools call a hosted platform with the token from `action-platform login`."""
    if remote is not None:
        client = Remote.from_credentials(remote or None)
        mcp = MCPServer(
            "action-platform",
            instructions=REMOTE_INSTRUCTIONS + RULES,
            version=__version__,
        )
        remote_tools.register(mcp, client)
        flow.register_rules(mcp)
        prompts.register_remote(mcp)
        mcp.middleware.append(_name_the_client(client))

        return mcp

    mcp = MCPServer(
        "action-platform", instructions=INSTRUCTIONS + RULES, version=__version__
    )

    matrix.register(mcp)
    project.register(mcp)
    flow.register(mcp)
    lifecycle.register(mcp)
    prompts.register(mcp)
    registry.installed().register(mcp, None, annotations.tool)

    return mcp


def _name_the_client(client: Remote):
    """Every message carries the session; its `clientInfo` is the program on the other side (Claude Code, Codex, Cursor…). Hand that name to the platform so the token page can show who uses it."""

    async def middleware(ctx, call_next):
        params = getattr(ctx.session, "client_params", None)
        info = getattr(params, "clientInfo", None)

        if info is not None and getattr(info, "name", None):
            version = getattr(info, "version", None)
            client.client = f"{info.name}/{version}" if version else str(info.name)

        return await call_next(ctx)

    return middleware


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="action-platform-mcp",
        description="Expose the Action Platform as MCP tools.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve streamable HTTP on --host/--port instead of stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--remote",
        nargs="?",
        const="",
        default=None,
        metavar="SERVER",
        help="Act on the hosted platform from `action-platform login` (optionally which one) instead of local files.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    bootstrap("mcp")
    args = parse_args(argv)
    mcp = build(remote=args.remote)

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
        return

    mcp.run()


if __name__ == "__main__":
    main()
