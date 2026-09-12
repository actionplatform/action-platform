"""Fixtures: a server over a tiny templates index, and a tool caller."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from action_platform.mcp import build  # noqa: E402

INDEX = """
[projects.web.python.fastapi]
default = true
description = "FastAPI"

[cloud.docker]
description = "Dockerfile"
languages = ["python"]
types = ["web"]

[service.postgres]
description = "db"
providers = ["docker"]
"""


def call(server, name: str, **kwargs):
    """Call a tool and return its structured result."""
    result = asyncio.run(server.call_tool(name, kwargs))

    if result.structured_content:
        return result.structured_content.get("result", result.structured_content)

    return json.loads(result.content[0].text)


def tool_names(server) -> set[str]:
    return {t.name for t in asyncio.run(server.list_tools())}


@pytest.fixture
def templates(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "index.toml").write_text(INDEX)
    monkeypatch.setattr(
        "action_platform.settings.settings.TEMPLATES_DIR", str(tmp_path)
    )

    return tmp_path


@pytest.fixture
def server():
    return build()
