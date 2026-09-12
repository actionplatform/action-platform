"""Prompts that put the tools in the order a platform task actually needs.

The costly mistakes live in the order: pushing before the user saw the
repository name, deploying before preflight, opening a pull request from a
branch that fails git-flow, releasing from the wrong branch.
"""

from __future__ import annotations

from typing import Any


def register(mcp: Any) -> None:
    @mcp.prompt(
        title="New service",
        description="Scaffold a service from the templates, add its cloud and dependencies, push on approval.",
    )
    def new_service(
        name: str = "", stack: str = "python", cloud: str = "", services: str = ""
    ) -> str:
        return (
            "Create a new service on the platform.\n\n"
            f"Name: {name or 'ask the user'}. Stack: {stack}. Cloud: {cloud or 'none yet'}. "
            f"Dependencies: {services or 'none'}.\n\n"
            "1. Call list_matrix and pick the `web` template for the stack; when "
            "several exist, ask which unless the user named one.\n"
            "2. Call init_project with type=web, the stack, the name and ci=github "
            "unless the user uses GitLab or Jenkins. Pass `cloud` only when one was named.\n"
            "3. For each dependency call service_add; pick the provider from context "
            "(docker locally, aws-* when the cloud is AWS).\n"
            "4. Show project_info and the files that matter: platform.toml, DEPLOY.md, "
            "requirements/ when a cloud was added.\n"
            "5. Say the repository that push_project would create — owner/name, public "
            "or private — and wait for a yes before calling it.\n\n"
            "Never call push_project in the same turn as init_project."
        )

    @mcp.prompt(
        title="Ship a feature",
        description="Start a git-flow branch, work, audit, and open the pull request on approval.",
    )
    def ship_feature(issue: str = "", summary: str = "") -> str:
        return (
            "Take a change from idea to pull request under git-flow.\n\n"
            f"Issue or ticket: {issue or 'ask the user — a branch needs a code'}. "
            f"Summary: {summary or 'ask what the change is'}.\n\n"
            "1. Decide the kind from the intent: new capability → feature, bug in "
            "development → bugfix, production incident → hotfix, everything else by "
            "its Conventional Commit type (chore, docs, refactor, test, ci, perf). "
            "gitflow_rules lists them.\n"
            "2. Call start_branch with the kind, the code and a two-word slug. It picks "
            "develop or main as base; never commit on those directly.\n"
            "3. Make the change in small Conventional Commits: `type(scope): description`, "
            "one concern per commit, files staged explicitly.\n"
            "4. Call gitflow_audit. Fix every problem it lists before going on.\n"
            "5. Call propose_pull_request and show head → base, title and body.\n"
            "6. On approval call open_pull_request. For release or hotfix branches, "
            "remind the user a second pull request into develop follows the merge."
        )

    @mcp.prompt(
        title="Cut a release",
        description="Preview the next version and changelog, publish only on approval; rc off main.",
    )
    def cut_release(level: str = "patch") -> str:
        return (
            f"Cut a {level} release.\n\n"
            "1. Call project_info and gitflow_audit; a dirty tree or a branch that "
            "fails git-flow stops here — say what to fix.\n"
            "2. Call release with dry_run=true. Report the current and next version "
            "and the changelog. On main/master the version is stable; on any other "
            "branch it is X.Y.Z-rc.N and the release is marked pre-release — say which "
            "case applies and why.\n"
            "3. An empty changelog means the commits are not Conventional Commits; "
            "stop and explain instead of releasing an empty entry.\n"
            "4. On approval call release again with dry_run=false and report the tag "
            "and the release URL. Mention that the publish workflow runs from the "
            "release (PyPI, npm, Packagist… for stable; the test index for rc)."
        )

    @mcp.prompt(
        title="Deploy",
        description="Preflight, deploy on approval, verify with diagnose.",
    )
    def deploy_project(stage: str = "") -> str:
        return (
            "Deploy the current version.\n\n"
            f"Stage: {stage or 'from the branch — main/master is prod, anything else dev'}.\n\n"
            "1. Call project_info; without a [deploy] target offer cloud_set and stop.\n"
            "2. Call deploy with dry_run=true. That is preflight: tooling, template "
            "validation, credentials. Relay any error verbatim; 'no provider installed' "
            "means the target's provider package is missing.\n"
            "3. Say the target, stage and version that would go live and wait for a yes.\n"
            "4. Call deploy with dry_run=false, then diagnose. Report status and URL.\n"
            "5. If diagnose is not ok, propose rollback — and confirm before calling it."
        )

    @mcp.prompt(
        title="Adopt an existing repository",
        description="Bring a repo that was not generated by the platform onto it, without touching its code.",
    )
    def adopt_repository(ci: str = "github") -> str:
        return (
            "Install the platform in an existing repository.\n\n"
            f"CI: {ci}.\n\n"
            "1. Call install_platform with dry_run=true. Show created and kept: "
            "nothing that exists is overwritten, and app code and deploy files are "
            "not touched.\n"
            "2. Explain what changes for the team from that moment: Conventional "
            "Commits, work on <kind>/<code> branches, main/develop refuse direct "
            "commits. If the repo used another commit style, say so before proceeding.\n"
            "3. On approval call install_platform with dry_run=false. Hooks are "
            "installed into .git/hooks; every other clone runs install_hooks once.\n"
            "4. Suggest the commit `chore(platform): install action-platform` on the "
            "default branch — one of the exceptions the hooks allow — then gitflow_audit."
        )

    @mcp.prompt(
        title="Fix git-flow",
        description="Diagnose and repair a branch that violates git-flow before it reaches a pull request.",
    )
    def fix_gitflow() -> str:
        return (
            "Repair git-flow violations on the current branch.\n\n"
            "1. Call gitflow_audit and gitflow_rules. Map each problem to a fix:\n"
            "   - wrong branch name → `git branch -m <kind>/<code>-slug`\n"
            "   - commits on main/develop → start_branch from the same base, "
            "cherry-pick them, reset the protected branch to origin\n"
            "   - non-conventional messages → `git commit --amend` for the last one, "
            "`git rebase -i` to reword older ones\n"
            "2. Every fix rewrites history: show the exact commands and the new "
            "messages, and wait for a yes. Never rewrite commits already pushed to a "
            "shared branch without saying so.\n"
            "3. If violations got through, the hooks are missing: call install_hooks.\n"
            "4. Re-run gitflow_audit until it reports ok."
        )
