"""Git-flow: start branches and audit what is on them."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.flow import gitflow, workflow
from action_platform.core.flow.workflow import GitFlow
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, WRITES_LOCAL

ProjectDir = Annotated[
    Optional[str], Field(description="Project directory; default is the cwd.")
]


def _root(project: Optional[str]) -> Path:
    return Path(project).resolve() if project else Path.cwd()


def register_rules(mcp: Any) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def gitflow_rules() -> dict:
        """The git-flow rules every project follows: branch kinds, their base and merge target, protected branches, commit format."""
        return {
            "kinds": sorted(gitflow.KINDS),
            "protected": sorted(gitflow.PROTECTED),
            "base": {
                "develop (or default branch when no develop)": sorted(
                    workflow.DEVELOP_BASED
                ),
                "default branch (main/master)": sorted(workflow.MAIN_BASED),
            },
            "merge_into": {
                "feature, bugfix, chore, docs, refactor, test, ci, perf": "develop (or default)",
                "release, hotfix": "main and develop",
                "develop": "main",
                "support": "nothing",
            },
            "branch_name": "<kind>/<code>[-slug], e.g. feature/42-login, hotfix/PROJ-7",
            "commit": "Conventional Commits 1.0.0: type(scope)!: description, types "
            + ", ".join(sorted(gitflow.TYPES)),
            "exceptions_on_protected": [
                "chore(release): X.Y.Z",
                "chore: bootstrap ...",
            ],
        }


def register(mcp: Any) -> None:
    register_rules(mcp)

    @mcp.tool(annotations=REACHES_OUT)
    def start_branch(
        kind: Annotated[
            str,
            Field(
                description="feature, bugfix, hotfix, release, support, chore, docs, refactor, test, ci, perf"
            ),
        ],
        code: Annotated[
            str,
            Field(description="Issue or ticket code: 42, PROJ-123, 1.4.0 for release"),
        ],
        slug: Annotated[
            Optional[str], Field(description="Optional words appended as a slug")
        ] = None,
        project: ProjectDir = None,
        push: Annotated[bool, Field(description="Push the new branch upstream")] = True,
    ) -> dict:
        """Start a git-flow branch: checkout the right base (develop or main), pull, create <kind>/<code>[-slug].

        Refuses a dirty working tree and an existing branch name. With push=true
        the branch is created on origin too.
        """
        branch = GitFlow(_root(project)).start(kind, code, slug, push=push)

        return {"branch": branch.name, "base": branch.base, "pushed": branch.pushed}

    @mcp.tool(annotations=READ_ONLY)
    def gitflow_audit(
        project: ProjectDir = None,
        since: Annotated[
            Optional[str],
            Field(
                description="Check commits after this ref; default is the merge base with develop/main"
            ),
        ] = None,
    ) -> dict:
        """Check the current branch name and its commits against git-flow and Conventional Commits.

        Returns every problem found; an empty list means the branch can be
        pushed and opened as a pull request.
        """
        report = GitFlow(_root(project)).audit(since=since)

        return {
            "branch": report.branch,
            "ok": report.ok,
            "checked_commits": report.checked_commits,
            "problems": report.problems,
        }

    @mcp.tool(annotations=READ_ONLY)
    def propose_pull_request(
        project: ProjectDir = None,
        base: Annotated[
            Optional[str], Field(description="Target branch; default from git-flow")
        ] = None,
        title: Annotated[
            Optional[str], Field(description="Default: first commit on the branch")
        ] = None,
    ) -> dict:
        """Compute the pull request for the current branch: target, title and a body grouped by commit type.

        Audits git-flow first and refuses a branch that does not pass. Nothing
        is opened; show the result and use open_pull_request on approval.
        """
        proposal = GitFlow(_root(project)).propose(base=base, title=title)

        return {
            "head": proposal.head,
            "base": proposal.base,
            "title": proposal.title,
            "body": proposal.body,
            "commits": proposal.commits,
        }

    @mcp.tool(annotations=REACHES_OUT)
    def open_pull_request(
        project: ProjectDir = None,
        base: Annotated[
            Optional[str], Field(description="Target branch; default from git-flow")
        ] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> dict:
        """Open the pull request on the source host, pushing the branch first if needed. Confirm with the user before calling."""
        ref = GitFlow(_root(project)).open_pr(
            base=base, title=title, body=body, draft=draft
        )

        return {"number": ref.number, "url": ref.url}

    @mcp.tool(annotations=WRITES_LOCAL)
    def install_hooks(project: ProjectDir = None) -> dict:
        """Install the platform git hooks into .git/hooks so git-flow is enforced before commit and push. Re-run after upgrading the CLI."""
        report = GitFlow(_root(project)).install_hooks()

        return {
            "installed": report.installed,
            "directory": str(report.directory) if report.directory else None,
            "preserved": report.preserved,
            "skipped": report.skipped,
        }
