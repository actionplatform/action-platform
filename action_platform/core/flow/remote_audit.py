"""The git-flow audit answered from a source host instead of a clone: the same rules over the commits the host compares."""

from __future__ import annotations

from action_platform.abc.source_host import ReadsRepository
from action_platform.core.context import CommitRow, TagRow
from action_platform.core.files import CONFIG_FILE
from action_platform.core.flow import gitflow as rules
from action_platform.core.flow.remote import RemoteRefs

BASES = ("develop", "main", "master")
PAGE = 100


def audit(
    reader: ReadsRepository,
    repo: str,
    branch: str,
    refs: RemoteRefs,
    tags: list[TagRow],
) -> rules.Report:
    """On a work branch, what it has that its base does not; on a protected branch, what came after the latest tag and after the commit that added platform.toml."""
    report = rules.Report(branch=branch)
    problem = rules.check_branch(branch)

    if problem:
        report.problems.append(problem)

    if branch in rules.current().protected:
        commits = _on_protected(reader, repo, branch, tags)
    else:
        base = next((b for b in BASES if b in refs.branches and b != branch), None)
        commits = reader.compare(repo, base, branch) if base else []

    report.checked_commits = len(commits)

    for commit in commits:
        problem = rules.check_commit(commit.subject)

        if problem:
            report.problems.append(problem)

    return report


def _on_protected(
    reader: ReadsRepository, repo: str, branch: str, tags: list[TagRow]
) -> list[CommitRow]:
    tag = tags[0].name if tags else None
    installed = _installed(reader, repo, branch)

    if installed is None:
        return reader.compare(repo, tag, branch) if tag else []

    after = reader.compare(repo, installed, branch)

    if not tag:
        return after

    since = {c.sha for c in reader.compare(repo, tag, branch)}

    return [c for c in after if c.sha in since]


def _installed(reader: ReadsRepository, repo: str, branch: str) -> str | None:
    touching = reader.commits(repo, branch, PAGE, path=CONFIG_FILE)

    if not touching or len(touching) >= PAGE:
        return None

    return touching[-1].sha
