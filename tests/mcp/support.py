"""Base class for MCP tests: a local server over a tiny templates index, plus tool/prompt callers."""

from __future__ import annotations

import asyncio
import json
import unittest

from tests.support import INDEX, TempCase

try:
    import mcp  # noqa: F401

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class McpCase(TempCase):
    def setUp(self):
        super().setUp()
        from action_platform.mcp import build

        (self.tmp_path / "index.json").write_text(INDEX)
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.tmp_path))
        self.server = build()

    def call(self, name: str, **kwargs):
        result = asyncio.run(self.server.call_tool(name, kwargs))

        if result.structured_content:
            return result.structured_content.get("result", result.structured_content)

        return json.loads(result.content[0].text)

    def tools(self) -> dict:
        return {t.name: t for t in asyncio.run(self.server.list_tools())}

    def prompt(self, prompt_name: str, **args) -> str:
        result = asyncio.run(self.server.get_prompt(prompt_name, args))

        return "\n".join(m.content.text for m in result.messages)
