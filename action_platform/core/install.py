"""Install the platform in an existing repository without touching its code or deploy files."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core import git, gitflow
from action_platform.core.exception import ActionPlatformError
from action_platform.core.templates import Matrix, load_matrix
from action_platform.settings import settings

MARKERS = [
    ("pyproject.toml", "python"),
    ("go.mod", "go"),
    ("package.json", "node"),
    ("composer.json", "php"),
    ("pom.xml", "java"),
    ("Cargo.toml", "rust"),
]

WORKFLOWS = ["code-quality.yml", "conventional-commit.yml", "gitflow.yml", "trivy.yml"]

CI_FILES = {
    "github": [".github/workflows/" + w for w in WORKFLOWS],
    "gitlab": [".gitlab-ci.yml"],
    "jenkins": ["Jenkinsfile"],
}

AGENTS = """# AGENTS.md

Rules an AI agent (or a new contributor) follows in this repo. Added by `action-platform install`; keep it current.

## Commits

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope)!: description` — `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. One commit per concern; stage files explicitly — never `git add .`. Enforced by git hooks (`action-platform install`) and CI.

## Branches

Git-flow: work on `<kind>/<code>[-slug]` started with `action-platform branch <kind> <code>`. Kinds: `feature bugfix hotfix release support chore docs refactor test ci perf`. Never commit on `main`, `master` or `develop`; `feature`/`bugfix` merge into `develop`, `release`/`hotfix` into `main` and `develop`.

## Platform

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


def detect_language(root: Path) -> str | None:
    for marker, language in MARKERS:
        if (root / marker).exists():
            return language

    return None


def install(
    root: Path,
    type_: str = "web",
    language: str | None = None,
    ci: str = "github",
    dry_run: bool = False,
) -> Plan:
    root = root.resolve()

    if not (root / ".git").exists():
        raise InstallError(f"{root} is not a git repository")

    language = language or detect_language(root)

    if language is None:
        raise InstallError(
            "cannot detect the language — pass --language "
            "(python, go, node, php, java, rust)"
        )

    if ci not in CI_FILES:
        raise InstallError(f"unknown ci: {ci} (available: {', '.join(CI_FILES)})")

    repo, matrix = load_matrix()
    source = _source_leaf(repo, matrix, language)
    plan = Plan(root=root, language=language, type=type_, ci=ci)

    _write(plan, settings.CONFIG_FILE, _platform_toml(root, type_, language), dry_run)
    _write(plan, settings.LAST_VERSION_FILE, "0.1.0\n", dry_run)
    _write(plan, "AGENTS.md", AGENTS, dry_run)

    _copy_tree(plan, source / ".code_quality", ".code_quality", dry_run)

    for rel in CI_FILES[ci]:
        _copy_file(plan, source / rel, rel, dry_run)

    if not dry_run:
        plan.hooks_installed = gitflow.install_hooks(root)

    return plan


def _source_leaf(repo: Path, matrix: Matrix, language: str) -> Path:
    for leaf in matrix.leaves:
        candidate = repo / leaf.directory / "{{cookiecutter.project_slug}}"
        cq = candidate / ".code_quality"

        if cq.is_dir() and _language_of(repo / leaf.directory) == language:
            return candidate

    raise InstallError(f"no template with language {language!r} to borrow config from")


def _language_of(leaf_dir: Path) -> str:
    import json

    try:
        return json.loads((leaf_dir / "cookiecutter.json").read_text()).get(
            "_language", ""
        )
    except (OSError, ValueError):
        return ""


def _platform_toml(root: Path, type_: str, language: str) -> str:
    remote = git.remote_url(cwd=root)
    repo = ""

    if "github.com" in remote:
        repo = remote.split("github.com", 1)[1].strip(":/").removesuffix(".git")

    text = (
        f'[project]\nname = "{root.name}"\ntype = "{type_}"\nlanguage = "{language}"\n'
    )

    if repo:
        text += f'\n[source_host]\nkind = "github"\nrepo = "{repo}"\n'

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
