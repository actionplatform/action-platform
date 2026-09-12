"""Tool surface and the read-only tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

from tests.mcp.conftest import call, tool_names


def test_tools_exposed(server):
    assert tool_names(server) == {
        "list_matrix",
        "init_project",
        "install_platform",
        "push_project",
        "cloud_set",
        "service_add",
        "project_info",
        "release",
        "deploy",
        "rollback",
        "diagnose",
        "gitflow_rules",
        "start_branch",
        "gitflow_audit",
        "install_hooks",
    }


def test_irreversible_tools_are_flagged(server):
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    assert tools["list_matrix"].annotations.read_only_hint
    assert tools["project_info"].annotations.read_only_hint
    assert tools["push_project"].annotations.open_world_hint
    assert tools["rollback"].annotations.destructive_hint
    assert not tools["init_project"].annotations.destructive_hint
    assert tools["start_branch"].annotations.open_world_hint
    assert tools["gitflow_audit"].annotations.read_only_hint
    assert tools["gitflow_rules"].annotations.read_only_hint
    assert not tools["install_platform"].annotations.open_world_hint
    assert not tools["install_hooks"].annotations.destructive_hint


def test_dry_run_is_the_default_where_it_matters(server):
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    for name in ("release", "deploy", "install_platform"):
        assert tools[name].input_schema["properties"]["dry_run"]["default"] is True


def test_list_matrix(server, templates):
    data = call(server, "list_matrix")

    assert data["projects"][0]["template"] == "fastapi"
    assert data["clouds"][0]["name"] == "docker"
    assert data["services"][0]["providers"] == ["docker"]


def test_project_info(server, tmp_path: Path):
    (tmp_path / "platform.toml").write_text(
        '[project]\nname = "x"\ntype = "web"\nlanguage = "python"\n'
        '[source_host]\nkind = "github"\nrepo = "acme/x"\n'
    )
    data = call(server, "project_info", project=str(tmp_path))

    assert data["type"] == "web"
    assert data["github_owner"] == "acme"


def test_gitflow_rules(server):
    rules = call(server, "gitflow_rules")

    assert "feature" in rules["kinds"]
    assert rules["protected"] == ["develop", "main", "master"]
    assert "hotfix" in rules["base"]["default branch (main/master)"]


def test_instructions_warn_before_reaching_out(server):
    text = server.instructions

    assert "push_project" in text
    assert "dry_run" in text


def test_install_platform_dry_run(server, templates, tmp_path: Path):
    import subprocess

    repo = tmp_path / "existing"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    proj = templates / "projects/web/python/fastapi/{{cookiecutter.project_slug}}"
    (proj / ".githooks").mkdir(parents=True)
    (proj / ".githooks/pre-commit").write_text("#!/bin/sh\nexit 0\n")
    (proj / ".code_quality").mkdir()
    (templates / "projects/web/python/fastapi/cookiecutter.json").write_text(
        '{"_language": "python"}'
    )

    data = call(server, "install_platform", project=str(repo))

    assert data["dry_run"] is True
    assert "platform.toml" in data["created"]
    assert not (repo / "platform.toml").exists()


def test_gitflow_audit_reports_problems(server, tmp_path: Path):
    import os
    import subprocess

    repo = tmp_path / "flow"
    repo.mkdir()
    env = {
        "PATH": os.environ["PATH"],
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }

    def run(*args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=repo, check=True, env=env, capture_output=True
        )

    run("init", "-q", "-b", "main")
    run("commit", "-q", "--allow-empty", "-m", "chore: bootstrap")
    run("tag", "v0.1.0")
    run("checkout", "-qb", "wip")
    run("commit", "-q", "--allow-empty", "-m", "did stuff")

    data = call(server, "gitflow_audit", project=str(repo), since="v0.1.0")

    assert data["ok"] is False
    assert any("not git-flow" in p for p in data["problems"])
    assert any("not a conventional commit" in p for p in data["problems"])
