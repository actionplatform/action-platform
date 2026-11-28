# Self-service deployments

Let developers and AI agents release and deploy on their own, within limits the organization sets.

## Context

Deploys go through one person or one team that holds the cloud credentials. Everyone else waits.

## Challenge

Handing out cloud credentials is a risk: keys leak, stay valid for months and do not say which app they were for. Keeping them central makes the platform team a queue.

## Solution

- **Roles decide who may deploy.** `deployer`, `admin` and `owner` hold `app.release`; `developer` branches, commits and edits configuration; `viewer` reads.
- **Scopes decide what may land where.** A `high` or `critical` scope refuses release candidates. Readiness blocks a release that cannot reach the scope.
- **Credentials never leave the platform.** On AWS, the platform signs a short-lived token per deploy and the account trusts it through OpenID Connect. Nobody holds a key.
- **Tokens are narrowed.** `action-platform login` mints a token with a scope (`read`, `write`, `release`, `admin`) and a reach (one organization, a project or an app) that never exceeds the role.
- **Agents follow the same rules.** The MCP tools `release` and `deploy` default to dry runs and act with the token's permissions.

## Workflow

1. An owner connects the cloud account once and creates the scopes of each app.
2. A deployer opens **Deployments → New deployment**, picks a release and a scope, runs preflight and deploys.
3. Or an AI agent, with a token limited to one app and the `release` scope, calls `release_readiness`, then `deploy` with a dry run, then the real deploy after the user approves.
4. The deployment history shows who deployed what, where and when.

## Benefits

- Developers deploy without asking for credentials.
- A token can be limited to one app and revoked from **Team → Sessions** at any time.
- A refused deploy states the missing permission or the failing check.
- AWS CloudTrail names the app in the token's subject, not a shared user.

## Related features

[Access control](concept_access_control.md) · [Scopes](concept_scopes.md) · [Cloud identity](concept_identity.md) · [MCP](use_mcp.md)

## Getting started

Invite members with the right roles under **Team → Members**, then follow [Deploy from the web](guide_first_deploy.md).
