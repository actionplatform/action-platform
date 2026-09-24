"""Git-flow applied to one repository: audit, branches, pull requests, hooks."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.context import PRRef
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow import gitflow as rules
from action_platform.core.flow.repository import Repository
from action_platform.core import extensions
from action_platform.core.release import changelog
from action_platform.core.wiring import Wiring, slot, wired
from action_platform.core.files import CONFIG_FILE


HOOK_MARK = "# action-platform hook"
HOOK_NAMES = ("pre-commit", "commit-msg", "pre-push")


class BranchError(ActionPlatformError):
    """Cannot start the branch."""


class PullRequestError(ActionPlatformError):
    """Cannot open the pull request."""


@dataclass
class Branch:
    name: str
    base: str
    pushed: bool = False


@dataclass
class Proposal:
    head: str
    base: str
    title: str
    body: str
    commits: list[str]


@dataclass
class HooksReport:
    installed: bool
    directory: Path | None = None
    preserved: list[str] = field(default_factory=list)
    skipped: str | None = None

    def __bool__(self) -> bool:
        return self.installed


def branch_name(kind: str, code: str, slug: str | None = None) -> str:
    if kind not in rules.current().kinds:
        raise BranchError(
            f"unknown branch kind: {kind} (available: {', '.join(sorted(rules.current().kinds))})"
        )

    code = code.strip()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", code):
        raise BranchError(f"invalid code: {code!r} (letters, digits, . _ -)")

    name = f"{kind}/{code}"

    if slug:
        name += "-" + slugify(slug)

    return name


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@slot("gitflow")
class GitFlow:
    wiring: Wiring | None = None

    def __init__(self, repo: Repository | Path) -> None:
        self.repo = repo if isinstance(repo, Repository) else Repository(repo)

    def default_branch(self) -> str:
        found = self.repo.default_branch()

        if found is None:
            raise BranchError("cannot find a default branch (main or master)")

        return found

    def has_develop(self) -> bool:
        return self.repo.remote_branch_exists("develop")

    def resolve_base(self, kind: str) -> str:
        """develop when it exists on origin, else the default branch; hotfix/support always the default."""
        default = self.default_branch()

        if kind in rules.current().main_based:
            return default

        return "develop" if self.has_develop() else default

    def audit(self, since: str | None = None) -> rules.Report:
        """The current branch and its commits: on a work branch since it left its base; on a protected branch only what came after the last tag and, once the platform is committed, after that commit."""
        branch = self.repo.branch
        report = rules.Report(branch=branch)
        problem = rules.check_branch(branch)

        if problem:
            report.problems.append(problem)

        if since is None and branch in rules.current().protected:
            commits = self._commits_on_protected()
        else:
            base = since or self._merge_base(branch)
            commits = self.repo.commits_since(base) if base else []

        report.checked_commits = len(commits)

        for subject in commits:
            problem = rules.check_commit(subject)

            if problem:
                report.problems.append(problem)

        return report

    def plan_branch(self, kind: str, code: str, slug: str | None = None) -> Branch:
        """Name and base a branch would get, without touching the repository."""
        return Branch(
            name=branch_name(kind, code, slug),
            base=self.resolve_base(kind),
            pushed=False,
        )

    def start(
        self, kind: str, code: str, slug: str | None = None, push: bool = True
    ) -> Branch:
        if not self.repo.is_clean():
            raise BranchError("working tree is dirty — commit or stash first")

        self.install_hooks()
        name = branch_name(kind, code, slug)
        self.repo.fetch(tags=False)

        if self.repo.remote_branch_exists(name) or self.repo.local_branch_exists(name):
            raise BranchError(f"branch {name} already exists")

        base = self.resolve_base(kind)
        self.repo.checkout(base)
        self.repo.run(["pull", "--ff-only", "--end-of-options", "origin", base])
        self.repo.checkout(name, create=True)

        if push:
            self.repo.push_upstream(name)

        return Branch(name=name, base=base, pushed=push)

    def propose(self, base: str | None = None, title: str | None = None) -> Proposal:
        """Everything a pull request needs, computed from the branch."""
        head = self.repo.branch

        if head in rules.current().protected:
            raise PullRequestError(
                f"'{head}' is a protected branch — start a branch first: action-platform branch feature <code>"
            )

        report = self.audit()

        if not report.ok:
            raise PullRequestError(
                "branch does not follow git-flow:\n  - "
                + "\n  - ".join(report.problems)
            )

        default = self.default_branch()
        has_develop = self.has_develop()
        allowed = rules.allowed_targets(head, default, has_develop)

        if base is None:
            if not allowed:
                raise PullRequestError(f"'{head}' has no merge target under git-flow")

            base = (
                default
                if default in allowed and head.startswith(("release/", "hotfix/"))
                else sorted(allowed)[0]
            )

        problem = rules.check_target(head, base, default, has_develop)

        if problem:
            raise PullRequestError(problem)

        commits = self.repo.commits_since(f"origin/{base}")

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
        self,
        base: str | None = None,
        title: str | None = None,
        body: str | None = None,
        draft: bool = False,
        config: Config | None = None,
    ) -> PRRef:
        config = config or Config.from_toml(self.repo.path / CONFIG_FILE)

        if config.source_host is None:
            raise PullRequestError(
                "platform.toml has no [source_host]; cannot open a pull request"
            )

        proposal = self.propose(base=base, title=title)

        if not self.repo.remote_branch_exists(proposal.head):
            self.repo.push_upstream(proposal.head)

        ctx = (self.wiring or wired).releaser(config, self.repo).context()

        ref = config.source_host.open_pr(
            ctx,
            base=proposal.base,
            head=proposal.head,
            title=proposal.title,
            body=body or proposal.body,
            draft=draft,
        )
        extensions.current().after_pull_request(ref)

        return ref

    def install_hooks(self) -> HooksReport:
        """Install the bundled hooks where git looks for them, keeping any hook the user already had: it is renamed to <name>.pre-action-platform and still runs after ours."""
        if not self.repo.exists():
            return HooksReport(installed=False)

        target, skipped = self._hooks_dir()

        if target is None:
            return HooksReport(installed=False, skipped=skipped)

        source = Path(__file__).resolve().parents[2] / "hooks"
        target.mkdir(parents=True, exist_ok=True)
        report = HooksReport(installed=True, directory=target)

        for name in HOOK_NAMES:
            dest = target / name

            if dest.exists() and HOOK_MARK not in dest.read_text(errors="replace"):
                keep = target / f"{name}.pre-action-platform"

                if not keep.exists():
                    dest.replace(keep)
                    keep.chmod(0o755)
                    report.preserved.append(name)

            shutil.copy2(source / name, dest)
            dest.chmod(0o755)

        shutil.copy2(source / "gitflow.sh", target / "gitflow.sh")
        (target / "gitflow.sh").chmod(0o755)

        return report

    def _hooks_dir(self) -> tuple[Path | None, str | None]:
        """Where git will look for hooks: core.hooksPath when set (Husky, lefthook…), else .git/hooks."""
        custom = self.repo.attempt(["config", "--get", "core.hooksPath"]).stdout.strip()

        if not custom:
            return self.repo.path / ".git" / "hooks", None

        path = (
            Path(custom)
            if Path(custom).is_absolute()
            else (self.repo.path / custom).resolve()
        )

        try:
            tracked = (
                self.repo.attempt(["ls-files", "--error-unmatch", str(path)]).returncode
                == 0
            )
        except OSError:
            tracked = False

        if tracked:
            return (
                None,
                f"core.hooksPath points at {custom}, which is versioned in the repository; hooks left untouched",
            )

        return path, None

    def _merge_base(self, branch: str) -> str | None:
        if branch in rules.current().protected:
            return self.repo.latest_tag()

        for candidate in (
            "origin/develop",
            "develop",
            "origin/main",
            "main",
            "origin/master",
            "master",
        ):
            base = self.repo.merge_base(branch, candidate)

            if base:
                return base

        return None

    def _commits_on_protected(self) -> list[str]:
        tag = self.repo.latest_tag()
        installed = self.repo.first_commit_adding(CONFIG_FILE)

        if installed is None:
            return self.repo.commits_since(tag) if tag else []

        revisions = ["HEAD", f"^{installed}"]

        if tag:
            revisions.append(f"^{tag}")

        return self.repo.subjects(*revisions, ancestry_path=installed)


def _body(commits: list[str]) -> str:
    rendered = changelog.render("next", commits)
    lines = rendered.splitlines()[2:]

    return "\n".join(lines).strip() or "\n".join(f"- {c}" for c in commits)
