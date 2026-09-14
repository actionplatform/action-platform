"""Install the platform in an existing repository without touching its code or deploy files."""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import GitFlow
from action_platform.core.manifest import toml_str
from action_platform.core.exception import ActionPlatformError
from action_platform.core.scaffold.templates import Matrix, load_matrix
from action_platform.core.scaffold.templates import detect_language as detect
from action_platform.settings import settings

MARKERS = [
    ("pyproject.toml", "python"),
    ("go.mod", "go"),
    ("package.json", "node"),
    ("composer.json", "php"),
    ("pom.xml", "java"),
    ("Cargo.toml", "rust"),
    ("Gemfile", "ruby"),
]

WORKFLOWS = ["code-quality.yml", "conventional-commit.yml", "gitflow.yml", "trivy.yml"]

CI_FILES = {
    "github": [".github/workflows/" + w for w in WORKFLOWS],
    "gitlab": [".gitlab-ci.yml"],
    "jenkins": ["Jenkinsfile"],
    "bitbucket": ["bitbucket-pipelines.yml"],
}

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


def detect_language(root: Path) -> str | None:
    return detect(root) or None


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

        ci = self.requested_ci or _existing_ci(self.root) or _ci_for_remote(self.repo)
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
        plan = Plan(root=self.root, language=language, type=self.type, ci=ci)

        _write(
            plan,
            settings.CONFIG_FILE,
            _platform_toml(
                self.repo, self.type, language, ci, self.name or self.root.name
            ),
            dry_run,
        )
        _write(
            plan, settings.LAST_VERSION_FILE, f"{_seed_version(self.repo)}\n", dry_run
        )
        _write(plan, "AGENTS.md", AGENTS, dry_run)

        if language:
            _copy_tree(plan, source / ".code_quality", ".code_quality", dry_run)

        for rel in CI_FILES[ci]:
            if not language and "code-quality" in rel:
                continue

            _copy_file(plan, source / rel, rel, dry_run)

        if not dry_run:
            report = GitFlow(self.repo).install_hooks()
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
    installer = Installer(root, type_=type_, language=language, ci=ci, name=name)

    return installer.plan() if dry_run else installer.apply()


def _seed_version(repo: Repository) -> str:
    """LAST_VERSION for a repository joining the platform: its newest vX.Y.Z tag, or 0.0.0 when it never released."""
    tag = repo.latest_tag(match="v[0-9]*")

    if tag and re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
        return tag.lstrip("v")

    return "0.0.0"


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


def _existing_ci(root: Path) -> str | None:
    path = root / settings.CONFIG_FILE

    if not path.exists():
        return None

    try:
        return tomllib.loads(path.read_text()).get("project", {}).get("ci") or None
    except tomllib.TOMLDecodeError:
        return None


def _platform_toml(
    repo: Repository, type_: str, language: str, ci: str, name: str | None = None
) -> str:
    remote = repo.remote_url()
    slug = ""

    if "github.com" in remote:
        slug = remote.split("github.com", 1)[1].strip(":/").removesuffix(".git")

    name = name or (slug.rsplit("/", 1)[-1] if slug else repo.path.name)
    text = f"[project]\nname = {toml_str(name)}\ntype = {toml_str(type_)}\nci = {toml_str(ci)}\nlanguage = {toml_str(language)}\n"

    if slug:
        text += f'\n[source_host]\nkind = "github"\nrepo = {toml_str(slug)}\n'

    text += '\n[release]\nstrategy = "semver"\nchangelog = "conventional"\n'

    return text


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
