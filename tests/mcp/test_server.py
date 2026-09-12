"""Tool surface and the read-only tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

from tests.mcp.conftest import call, tool_names


def test_tools_exposed(server):
    assert tool_names(server) == {
        "list_matrix",
        "init_project",
        "push_project",
        "cloud_set",
        "service_add",
        "project_info",
        "release",
        "deploy",
        "rollback",
        "diagnose",
    }


def test_irreversible_tools_are_flagged(server):
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    assert tools["list_matrix"].annotations.read_only_hint
    assert tools["project_info"].annotations.read_only_hint
    assert tools["push_project"].annotations.open_world_hint
    assert tools["rollback"].annotations.destructive_hint
    assert not tools["init_project"].annotations.destructive_hint


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


def test_instructions_warn_before_reaching_out(server):
    text = server.instructions

    assert "push_project" in text
    assert "dry_run" in text
