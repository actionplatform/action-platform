"""Install the platform in an existing repository without touching its code or deploy files."""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.flow.repository import Repository
from action_platform.core.manifest import toml_str
from action_platform.core.exception import ActionPlatformError
from action_platform.core.release.versioning import SEMVER_RE
from action_platform.core.scaffold.catalog import Matrix, load_matrix
from action_platform.core.scaffold.language import detect_language
from action_platform.core.wiring import slot, wired
from action_platform.core.files import CONFIG_FILE, LAST_VERSION_FILE

WORKFLOWS = ["code-quality.yml", "conventional-commit.yml", "gitflow.yml", "trivy.yml"]

CI_FILES = {
    "github": [".github/workflows/" + w for w in WORKFLOWS],
    "gitlab": [".gitlab-ci.yml"],
    "jenkins": ["Jenkinsfile"],
    "bitbucket": ["bitbucket-pipelines.yml"],
    "none": [],
}

CI_MARKERS = {
    "jenkins": "Jenkinsfile",
    "gitlab": ".gitlab-ci.yml",
    "bitbucket": "bitbucket-pipelines.yml",
    "github": ".github/workflows",
}

JENKINS_STAGES = """library identifier: 'ci-jenkins@v1',
        retriever: modernSCM([$class: 'GitSCMSource',
                              remote: 'https://github.com/actionplatform/ci-jenkins.git'])

stage('Check') {{
    steps {{
        apSetup(language: '{language}')
        apCheck(language: '{language}')
    }}
}}
stage('Commits') {{
    when {{ changeRequest() }}
    steps {{ apConventionalCommit() }}
}}
stage('Git-flow') {{
    when {{ changeRequest() }}
    steps {{ apGitflow() }}
}}
"""

AGENTS = """# AGENTS.md

Rules an AI agent (or a new contributor) follows in this repo. Added by `action-platform install`; keep it current.

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope)!: description` — `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. One commit per concern; stage files explicitly — never `git add .`. Enforced by git hooks (`action-platform install`) and CI.

Git-flow: work on `<kind>/<code>[-slug]` started with `action-platform branch <kind> <code>`. Kinds: `feature bugfix hotfix release support chore docs refactor test ci perf`. Never commit on `main`, `master` or `develop`; `feature`/`bugfix` merge into `develop`, `release`/`hotfix` into `main` and `develop`.

`platform.toml` declares the project; `action-platform release` cuts versions from `LAST_VERSION`; `action-platform gitflow` audits a branch before a pull request.
"""


class InstallError(ActionPlatformError):
    """Cannot install the platform in this directory."""


@dataclass
class Plan:
    root: Path
    language: str
    type: str
    ci: str
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    hooks_installed: bool = False
    hooks_preserved: list[str] = field(default_factory=list)
    hooks_skipped: str | None = None
    detected_ci: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ci_snippet: str = ""

    def report(self) -> dict:
        """The CI the plan settled on and what it found on the way: the CIs already in the repository, the warnings, the stages to paste into a kept Jenkinsfile."""
        return {
            "ci": self.ci,
            "detected_ci": self.detected_ci,
            "warnings": self.warnings,
            "ci_snippet": self.ci_snippet,
        }


@slot("installer")
class Installer:
    """Bring an existing repository onto the platform: platform.toml, LAST_VERSION, AGENTS.md, the quality config and CI files borrowed from the closest template, the git hooks. `plan()` says what would happen; `apply()` does it."""

    def __init__(
        self,
        root: Path,
        type_: str = "web",
        language: str | None = None,
        ci: str | None = None,
        name: str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.repo = Repository(self.root)
        self.type = type_
        self.requested_language = language
        self.requested_ci = ci
        self.name = name

    def plan(self) -> Plan:
        return self._run(dry_run=True)

    def apply(self) -> Plan:
        return self._run(dry_run=False)

    def _run(self, dry_run: bool) -> Plan:
        if not self.repo.exists():
            raise InstallError(f"{self.root} is not a git repository")

        detected = ci_in_repository(self.root)
        ci = self.requested_ci or _existing_ci(self.root)

        if not ci and len(detected) > 1:
            raise InstallError(
                f"the repository already runs more than one CI ({', '.join(CI_MARKERS[d] for d in detected)}); "
                "pass --ci with the one the platform's checks belong to, or --ci none"
            )

        ci = ci or (detected[0] if detected else _ci_for_remote(self.repo))
        language = (
            ""
            if self.requested_language == "none"
            else (self.requested_language or detect_language(self.root) or "")
        )

        if ci not in CI_FILES:
            raise InstallError(f"unknown ci: {ci} (available: {', '.join(CI_FILES)})")

        repo, matrix = load_matrix()
        source = (
            _source_leaf(repo, matrix, language)
            if language
            else _any_leaf(repo, matrix)
        )
        plan = Plan(
            root=self.root,
            language=language,
            type=self.type,
            ci=ci,
            detected_ci=detected,
            warnings=[
                f"{CI_MARKERS[d]} found; installing {ci} CI files runs a second CI next to it"
                for d in detected
                if d != ci and ci != "none"
            ],
        )

        _write(
            plan,
            CONFIG_FILE,
            _platform_toml(
                self.repo, self.type, language, ci, self.name or self.root.name
            ),
            dry_run,
        )
        _write(plan, LAST_VERSION_FILE, f"{_seed_version(self.repo)}\n", dry_run)
        _write(plan, "AGENTS.md", AGENTS, dry_run)

        if language:
            _copy_tree(plan, source / ".code_quality", ".code_quality", dry_run)

        for rel in CI_FILES[ci]:
            if not language and "code-quality" in rel:
                continue

            _copy_file(plan, source / rel, rel, dry_run)

        if ci == "jenkins" and (self.root / "Jenkinsfile").is_file():
            plan.ci_snippet = JENKINS_STAGES.format(language=language)

        if not dry_run:
            report = wired.gitflow(self.repo).install_hooks()
            plan.hooks_installed = bool(report)
            plan.hooks_preserved = list(report.preserved)
            plan.hooks_skipped = report.skipped

        return plan


def install(
    root: Path,
    type_: str = "web",
    language: str | None = None,
    ci: str | None = None,
    dry_run: bool = False,
    name: str | None = None,
) -> Plan:
    installer = wired.installer(root, type_=type_, language=language, ci=ci, name=name)

    return installer.plan() if dry_run else installer.apply()


def _seed_version(repo: Repository) -> str:
    """LAST_VERSION for a repository joining the platform: its newest release tag among all tags, `v1.2.3` or `1.2.3`, a pre-release only when no stable release follows it; 0.0.0 when it never released."""
    found = [
        m for m in (SEMVER_RE.match(t.removeprefix("v")) for t in repo.tags()) if m
    ]

    if not found:
        return "0.0.0"

    return max(found, key=_precedence).group(0)


def _precedence(found: re.Match) -> tuple:
    major, minor, patch, pre = found.groups()
    identifiers = tuple(
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in (pre or "").split(".")
    )

    return int(major), int(minor), int(patch), pre is None, identifiers


def _any_leaf(repo: Path, matrix: Matrix) -> Path:
    for leaf in matrix.leaves:
        candidate = repo / leaf.directory / "{{cookiecutter.project_slug}}"

        if candidate.is_dir():
            return candidate

    raise InstallError("no template to borrow CI files from")


def _source_leaf(repo: Path, matrix: Matrix, language: str) -> Path:
    for leaf in matrix.leaves:
        candidate = repo / leaf.directory / "{{cookiecutter.project_slug}}"
        cq = candidate / ".code_quality"

        if cq.is_dir() and _language_of(repo / leaf.directory) == language:
            return candidate

    raise InstallError(f"no template with language {language!r} to borrow config from")


def _language_of(leaf_dir: Path) -> str:
    try:
        return json.loads((leaf_dir / "cookiecutter.json").read_text()).get(
            "_language", ""
        )
    except (OSError, ValueError):
        return ""


def _ci_for_remote(repo: Repository) -> str:
    """The CI that matches where the repository lives: GitLab CI, Bitbucket Pipelines, else GitHub Actions."""
    remote = repo.remote_url()

    if "gitlab" in remote:
        return "gitlab"

    if "bitbucket" in remote:
        return "bitbucket"

    return "github"


def ci_in_repository(root: Path) -> list[str]:
    """The CIs the repository already has, from their files."""
    found = [
        kind
        for kind, marker in CI_MARKERS.items()
        if kind != "github" and (root / marker).is_file()
    ]
    workflows = root / CI_MARKERS["github"]

    if workflows.is_dir() and any(
        p.suffix in (".yml", ".yaml") for p in workflows.iterdir()
    ):
        found.append("github")

    return found


def _existing_ci(root: Path) -> str | None:
    path = root / CONFIG_FILE

    if not path.exists():
        return None

    try:
        return tomllib.loads(path.read_text()).get("project", {}).get("ci") or None
    except tomllib.TOMLDecodeError:
        return None


def _platform_toml(
    repo: Repository, type_: str, language: str, ci: str, name: str | None = None
) -> str:
    kind, slug, base_url = _source_host(repo.remote_url())
    name = name or (slug.rsplit("/", 1)[-1] if slug else repo.path.name)
    text = f"[project]\nname = {toml_str(name)}\ntype = {toml_str(type_)}\nci = {toml_str(ci)}\nlanguage = {toml_str(language)}\n"

    if slug:
        text += f"\n[source_host]\nkind = {toml_str(kind)}\nrepo = {toml_str(slug)}\n"

        if base_url:
            text += f"base_url = {toml_str(base_url)}\n"

    text += '\n[release]\nstrategy = "semver"\nchangelog = "conventional"\n'

    return text


def _source_host(remote: str) -> tuple[str, str, str]:
    """The source host a remote URL points at — kind, `owner/name` path and, for a self-hosted GitLab, its base URL; empty when it is none the platform knows."""
    found = re.match(
        r"^(?:[a-z+]+://)?(?:[^@/]+@)?(?P<host>[^:/]+)(?::\d+)?[:/](?P<path>.+?)(?:\.git)?/?$",
        remote.strip(),
    )

    if not found:
        return "", "", ""

    host, path = found.group("host").lower(), found.group("path").strip("/")

    if host == "github.com":
        return "github", path, ""

    if host == "bitbucket.org":
        return "bitbucket", path, ""

    if host == "gitlab.com":
        return "gitlab", path, ""

    if "gitlab" in host:
        return "gitlab", path, f"https://{host}"

    return "", "", ""


def _write(plan: Plan, rel: str, content: str, dry_run: bool) -> None:
    target = plan.root / rel

    if target.exists():
        plan.skipped.append(rel)
        return

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    plan.created.append(rel)


def _copy_file(plan: Plan, source: Path, rel: str, dry_run: bool) -> None:
    if not source.exists():
        return

    target = plan.root / rel

    if target.exists():
        plan.skipped.append(rel)
        return

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    plan.created.append(rel)


def _copy_tree(plan: Plan, source: Path, rel: str, dry_run: bool) -> None:
    if not source.is_dir():
        return

    target = plan.root / rel

    if target.exists():
        plan.skipped.append(rel + "/")
        return

    if not dry_run:
        shutil.copytree(source, target)

    plan.created.append(rel + "/")
