"""action_platform.mcp.tools.remote — every tool reaches the hosted API through the Remote client with the expected call."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any

from tests.mcp.support import HAS_MCP

LISTS = {"apps", "commits", "branches", "tags", "releases", "deploy", "diagnose"}


class FakeRemote:
    server = "https://p.example"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

            if name == "whoami":
                return {"user": {"email": "me@example.com", "name": "Me"}}

            if name in LISTS:
                return []

            return {"called": name}

        return method


CASES: list[tuple[str, dict[str, Any], str, tuple, dict]] = [
    ("list_apps", {}, "apps", (), {}),
    (
        "add_app",
        {"url": "https://x/y.git"},
        "add_app",
        ("https://x/y.git", None, None),
        {},
    ),
    (
        "add_app",
        {"url": "https://x/y.git", "install_type": "web", "install_ci": "gitlab"},
        "add_app",
        ("https://x/y.git", None, {"type": "web", "ci": "gitlab"}),
        {},
    ),
    ("remove_app", {"id": "a1"}, "remove_app", ("a1",), {}),
    ("sync_app", {"id": "a1"}, "sync_app", ("a1",), {}),
    ("app_info", {"id": "a1"}, "app", ("a1",), {}),
    ("gitflow_audit", {"id": "a1"}, "gitflow", ("a1",), {}),
    ("app_commits", {"id": "a1", "limit": 3}, "commits", ("a1", 3), {}),
    ("app_branches", {"id": "a1"}, "branches", ("a1",), {}),
    ("app_tags", {"id": "a1"}, "tags", ("a1",), {}),
    ("app_releases", {"id": "a1"}, "releases", ("a1",), {}),
    ("release", {"id": "a1"}, "release", ("a1", "patch", True, None), {}),
    (
        "release",
        {"id": "a1", "level": "minor", "dry_run": False, "branch": "main"},
        "release",
        ("a1", "minor", False, "main"),
        {},
    ),
    ("deploy", {"id": "a1"}, "deploy", ("a1", None, True), {}),
    ("diagnose", {"id": "a1"}, "diagnose", ("a1", None), {}),
    (
        "start_branch",
        {"id": "a1", "kind": "feature", "code": "42"},
        "start_branch",
        ("a1", "feature", "42", None, True),
        {},
    ),
    (
        "checkout_branch",
        {"id": "a1", "branch": "develop"},
        "checkout",
        ("a1", "develop"),
        {},
    ),
    ("propose_pull_request", {"id": "a1"}, "propose_pr", ("a1", None, None), {}),
    (
        "open_pull_request",
        {"id": "a1", "title": "feat: x", "draft": True},
        "open_pr",
        ("a1", None, "feat: x", None, True),
        {},
    ),
    ("read_manifest", {"id": "a1"}, "manifest", ("a1",), {}),
    (
        "write_manifest",
        {"id": "a1", "content": "[project]\n"},
        "write_manifest",
        ("a1", "[project]\n"),
        {},
    ),
    (
        "set_cloud",
        {"id": "a1", "target": "docker"},
        "set_cloud",
        ("a1", "docker", None),
        {},
    ),
    (
        "add_service",
        {"id": "a1", "name": "postgres", "provider": "docker", "source": "acme"},
        "add_service",
        ("a1", "postgres", "docker", "acme"),
        {},
    ),
    (
        "commit_changes",
        {"id": "a1", "message": "chore: x"},
        "commit",
        ("a1", "chore: x", False, None, False),
        {},
    ),
    (
        "commit_changes",
        {
            "id": "a1",
            "message": "chore: x",
            "branch_kind": "chore",
            "branch_code": "7",
            "pull_request": True,
        },
        "commit",
        ("a1", "chore: x", False, {"kind": "chore", "code": "7", "slug": None}, True),
        {},
    ),
    ("list_matrix", {}, "matrix", (), {}),
]


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class RemoteToolsTest(unittest.TestCase):
    def setUp(self):
        from action_platform.mcp.server import MCPServer, REMOTE_INSTRUCTIONS
        from action_platform.mcp.tools import flow, remote as remote_tools

        self.fake = FakeRemote()
        self.server = MCPServer("action-platform", instructions=REMOTE_INSTRUCTIONS)
        remote_tools.register(self.server, self.fake)
        flow.register_rules(self.server)

    def call(self, tool: str, args: dict[str, Any]):
        result = asyncio.run(self.server.call_tool(tool, args))

        if result.structured_content:
            return result.structured_content.get("result", result.structured_content)

        return json.loads(result.content[0].text)

    def test_every_tool_calls_the_client(self):
        for tool, args, method, expected_args, expected_kwargs in CASES:
            with self.subTest(tool=tool, args=args):
                self.call(tool, args)
                self.assertEqual(
                    self.fake.calls[-1], (method, expected_args, expected_kwargs)
                )

    def test_whoami_reports_server_and_account(self):
        self.assertEqual(
            self.call("whoami", {}),
            {"server": "https://p.example", "email": "me@example.com", "name": "Me"},
        )

    def test_init_app_sends_the_whole_request(self):
        self.call(
            "init_app",
            {
                "type": "web",
                "name": "Orders",
                "stack": "python",
                "cloud": "docker",
                "source": "acme",
                "push": True,
                "private": True,
            },
        )

        name, args, _ = self.fake.calls[-1]
        self.assertEqual(name, "init")
        self.assertEqual(
            args[0],
            {
                "type": "web",
                "stack": "python",
                "template": None,
                "name": "Orders",
                "ci": "github",
                "cloud": "docker",
                "source": "acme",
                "push": True,
                "private": True,
            },
        )

    def test_remove_app_returns_what_was_removed(self):
        self.assertEqual(self.call("remove_app", {"id": "a1"}), {"removed": "a1"})

    def test_remote_surface_excludes_local_only_tools(self):
        names = {t.name for t in asyncio.run(self.server.list_tools())}

        self.assertLessEqual(
            {
                "whoami",
                "list_apps",
                "add_app",
                "sync_app",
                "release",
                "deploy",
                "gitflow_rules",
                "commit_changes",
            },
            names,
        )
        self.assertNotIn("init_project", names)
        self.assertNotIn("install_hooks", names)
