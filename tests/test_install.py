"""Installing the platform in an existing repo: creates what is missing, keeps what exists."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from action_platform.core.scaffold import install
from action_platform.core.scaffold.install import InstallError


@pytest.fixture
def templates(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "templates"
    leaf = root / "projects/web/python/fastapi"
    proj = leaf / "{{cookiecutter.project_slug}}"
    (leaf).mkdir(parents=True)
    (leaf / "cookiecutter.json").write_text('{"_language": "python"}')
    (proj / ".code_quality").mkdir(parents=True)
    (proj / ".code_quality/ruff.toml").write_text("line-length = 79\n")
    (proj / ".github/workflows").mkdir(parents=True)
    for w in ["code-quality.yml", "gitflow.yml"]:
        (proj / ".github/workflows" / w).write_text("name: x\n")
    (proj / ".gitlab-ci.yml").write_text("image: x\n")
    (root / "index.toml").write_text(
        '[projects.web.python.fastapi]\ndefault = true\ndescription = "x"\n'
    )
    monkeypatch.setattr("action_platform.settings.settings.TEMPLATES_DIR", str(root))

    return root


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "existing"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:acme/existing.git"],
        cwd=root,
        check=True,
    )
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/workflows/code-quality.yml").write_text("name: theirs\n")

    return root


def test_creates_missing_keeps_existing(repo: Path, templates: Path):
    plan = install.install(repo)

    assert plan.language == "python"
    assert "platform.toml" in plan.created
    assert ".code_quality/" in plan.created
    assert ".github/workflows/gitflow.yml" in plan.created
    assert ".github/workflows/code-quality.yml" in plan.skipped
    assert (repo / ".github/workflows/code-quality.yml").read_text() == "name: theirs\n"
    assert 'repo = "acme/existing"' in (repo / "platform.toml").read_text()
    assert 'ci = "github"' in (repo / "platform.toml").read_text()
    assert plan.hooks_installed
    assert (repo / ".git/hooks/pre-commit").exists()
    assert (repo / ".git/hooks/gitflow.sh").exists()
    assert not (repo / ".githooks").exists()
    assert (
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
        ).stdout.count(".git/")
        == 0
    )


def test_dry_run_writes_nothing(repo: Path, templates: Path):
    plan = install.install(repo, dry_run=True)

    assert "platform.toml" in plan.created
    assert not (repo / "platform.toml").exists()


def test_gitlab_ci(repo: Path, templates: Path):
    plan = install.install(repo, ci="gitlab")

    assert ".gitlab-ci.yml" in plan.created


def test_errors(tmp_path: Path, templates: Path):
    with pytest.raises(InstallError, match="not a git repository"):
        install.install(tmp_path)

    bare = tmp_path / "nolang"
    bare.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=bare, check=True)

    plan = install.install(bare)
    assert plan.language == ""
    assert "platform.toml" in plan.created
    assert not (bare / ".code_quality").exists()
    assert not (bare / ".github/workflows/code-quality.yml").exists()
    assert (bare / ".github/workflows/gitflow.yml").exists()
    assert 'language = ""' in (bare / "platform.toml").read_text()


def test_hooks_are_refreshed_from_the_package(repo: Path, templates: Path):
    install.install(repo)
    (repo / ".git/hooks/pre-commit").write_text("broken")

    install.install(repo)

    assert "gitflow_branch" in (repo / ".git/hooks/pre-commit").read_text()


def test_ci_comes_from_platform_toml(repo: Path, templates: Path):
    (repo / "platform.toml").write_text(
        '[project]\nname = "x"\nci = "gitlab"\nlanguage = "python"\n'
    )

    plan = install.install(repo)

    assert plan.ci == "gitlab"
    assert ".gitlab-ci.yml" in plan.created


def test_last_version_starts_at_zero_or_at_the_newest_tag(
    tmp_path: Path, templates: Path
):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "pyproject.toml").write_text('[project]\nname = "fresh"\n')
    subprocess.run(["git", "init", "-q"], cwd=fresh, check=True)
    install.install(fresh)
    assert (fresh / "LAST_VERSION").read_text() == "0.0.0\n"

    tagged = tmp_path / "tagged"
    tagged.mkdir()
    (tagged / "pyproject.toml").write_text('[project]\nname = "tagged"\n')
    subprocess.run(["git", "init", "-q"], cwd=tagged, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "chore: first",
        ],
        cwd=tagged,
        check=True,
    )
    subprocess.run(["git", "tag", "v2.3.4"], cwd=tagged, check=True)
    install.install(tagged)
    assert (tagged / "LAST_VERSION").read_text() == "2.3.4\n"


def test_platform_toml_escapes_user_values(tmp_path: Path, templates: Path):
    import tomllib

    from action_platform.core.manifest import (
        check_owner,
        toml_str,
        write_deploy_target,
        write_source_host,
    )
    from action_platform.core.exception import TemplateError

    evil = 'x"\n[deploy]\ntarget = "aws/lambda'
    assert tomllib.loads(f"v = {toml_str(evil)}\n")["v"] == evil

    manifest = tmp_path / "platform.toml"
    manifest.write_text('[project]\nname = "demo"\n')
    write_source_host(manifest, "github", "acme/orders")
    write_deploy_target(manifest, evil)
    data = tomllib.loads(manifest.read_text())
    assert data["deploy"]["target"] == evil
    assert data["source_host"]["repo"] == "acme/orders"

    with pytest.raises(TemplateError):
        write_source_host(manifest, "github", 'acme/or"ders')
    with pytest.raises(TemplateError):
        check_owner("-x")
