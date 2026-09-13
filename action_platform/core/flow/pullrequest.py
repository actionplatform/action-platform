"""Open a pull request the git-flow way: audit the branch, pick the target, describe the commits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from action_platform.core.flow import branching, git, gitflow
from action_platform.core.release import changelog
from action_platform.core.config import Config
from action_platform.core.context import PRRef
from action_platform.core.exception import ActionPlatformError
from action_platform.core.release.release import build_context
from action_platform.settings import settings


class PullRequestError(ActionPlatformError):
    """Cannot open the pull request."""


@dataclass
class Proposal:
    head: str
    base: str
    title: str
    body: str
    commits: list[str]


def propose(cwd: Path, base: str | None = None, title: str | None = None) -> Proposal:
    """Everything a PR needs, computed from the branch — no remote call."""
    head = git.current_branch(cwd=cwd)

    if head in gitflow.PROTECTED:
        raise PullRequestError(
            f"'{head}' is a protected branch — start a branch first: action-platform branch feature <code>"
        )

    report = gitflow.audit(cwd)

    if not report.ok:
        raise PullRequestError(
            "branch does not follow git-flow:\n  - " + "\n  - ".join(report.problems)
        )

    default = branching._default_branch(cwd)
    has_develop = branching._remote_has(cwd, "develop")
    allowed = gitflow.allowed_targets(head, default, has_develop)

    if base is None:
        if not allowed:
            raise PullRequestError(f"'{head}' has no merge target under git-flow")

        base = (
            default
            if default in allowed and head.startswith(("release/", "hotfix/"))
            else sorted(allowed)[0]
        )

    problem = gitflow.check_target(head, base, default, has_develop)

    if problem:
        raise PullRequestError(problem)

    commits = git.commits_since(f"origin/{base}", cwd=cwd)

    if not commits:
        raise PullRequestError(f"no commits on {head} beyond origin/{base}")

    return Proposal(
        head=head,
        base=base,
        title=title or commits[-1],
        body=_body(commits),
        commits=commits,
    )


def open_pr(
    cwd: Path,
    base: str | None = None,
    title: str | None = None,
    body: str | None = None,
    draft: bool = False,
    config: Config | None = None,
) -> PRRef:
    config = config or Config.from_toml(cwd / settings.CONFIG_FILE)

    if config.source_host is None:
        raise PullRequestError(
            "platform.toml has no [source_host]; cannot open a pull request"
        )

    proposal = propose(cwd, base=base, title=title)

    if not branching._remote_has(cwd, proposal.head):
        git.push_upstream(proposal.head, cwd)

    ctx = build_context(config, cwd)

    return config.source_host.open_pr(
        ctx,
        base=proposal.base,
        head=proposal.head,
        title=proposal.title,
        body=body or proposal.body,
        draft=draft,
    )


def _body(commits: list[str]) -> str:
    rendered = changelog.render("next", commits)
    lines = rendered.splitlines()[2:]

    return "\n".join(lines).strip() or "\n".join(f"- {c}" for c in commits)
