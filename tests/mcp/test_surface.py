"""Every tool on both surfaces declares what it takes and what it answers with."""

import asyncio
import unittest

from action_platform.remote.client import Remote
from tests.mcp.support import HAS_MCP

if HAS_MCP:
    from action_platform.mcp import server


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class SurfaceTest(unittest.TestCase):
    def setUp(self):
        self.original = Remote.from_credentials
        Remote.from_credentials = classmethod(lambda cls, s=None: Remote.__new__(cls))

    def tearDown(self):
        Remote.from_credentials = self.original

    def test_every_tool_has_input_and_output_schemas(self):
        for remote in (None, ""):
            tools = asyncio.run(server.build(remote).list_tools())

            self.assertGreaterEqual(len(tools), 17)

            for t in tools:
                with self.subTest(remote=remote, tool=t.name):
                    self.assertEqual(t.input_schema.get("type"), "object")
                    self.assertIsNotNone(t.output_schema, "no output schema")
                    self.assertTrue(t.description)
                    self.assertIsNotNone(t.annotations)

    def test_both_servers_offer_prompts(self):
        for remote, expected in ((None, "new_service"), ("", "new_app")):
            names = {p.name for p in asyncio.run(server.build(remote).list_prompts())}

            self.assertIn(expected, names)
            self.assertGreaterEqual(len(names), 6)

    def test_rules_ride_with_the_instructions(self):
        for remote in (None, ""):
            text = server.build(remote).instructions or ""

            self.assertIn("Git-flow always", text)
            self.assertIn("only through these tools", text)
