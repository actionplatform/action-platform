"""Prompts name the tools they lead to, in order, and stop before anything irreversible."""

from __future__ import annotations

import asyncio


def _text(server, prompt: str, **args) -> str:
    result = asyncio.run(server.get_prompt(prompt, args))

    return "\n".join(m.content.text for m in result.messages)


def test_prompts_exposed(server):
    names = {p.name for p in asyncio.run(server.list_prompts())}

    assert names == {
        "new_service",
        "ship_feature",
        "cut_release",
        "deploy_project",
        "adopt_repository",
        "fix_gitflow",
    }


def test_new_service_pushes_last_and_only_on_yes(server):
    text = _text(
        server, "new_service", name="orders", stack="python", cloud="aws/lambda"
    )

    assert (
        text.index("list_matrix")
        < text.index("init_project")
        < text.index("push_project")
    )
    assert "Never call push_project in the same turn" in text


def test_ship_feature_audits_before_pull_request(server):
    text = _text(server, "ship_feature", issue="42")

    assert (
        text.index("start_branch")
        < text.index("gitflow_audit")
        < text.index("propose_pull_request")
        < text.index("open_pull_request")
    )


def test_cut_release_previews_and_explains_rc(server):
    text = _text(server, "cut_release", level="minor")

    assert "dry_run=true" in text and "dry_run=false" in text
    assert "rc.N" in text


def test_deploy_preflights_then_confirms(server):
    text = _text(server, "deploy_project")

    assert (
        text.index("dry_run=true")
        < text.index("wait for a yes")
        < text.index("dry_run=false")
    )
    assert "diagnose" in text
