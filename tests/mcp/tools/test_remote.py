"""action_platform.mcp.tools.remote — every tool reaches the hosted API through the Remote client with the expected call."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any, get_type_hints

from pydantic import TypeAdapter

from action_platform.remote.client import Remote

from tests.mcp.support import HAS_MCP

if HAS_MCP:
    from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from tests.support import TempCase, git, repo_with_origin

LISTS = {
    "apps",
    "commits",
    "branches",
    "tags",
    "releases",
    "deploy",
    "diagnose",
    "organizations",
    "projects",
    "teams",
    "members",
}


APP = {"id": "a1", "name": "orders", "url": "https://x/y.git", "default_branch": "main"}
CREATED = {"id": "n1", "name": "New", "slug": "new"}
FLOW = {"branch": "feature/1", "base": "develop", "pushed": True}
PR = {"head": "feature/1", "base": "develop", "title": "t", "body": "b", "commits": []}
SHAPES: dict[str, Any] = {
    "add_app": {"id": "d1", "registry_id": "a1", "name": "orders"},
    "init": {"id": "d1", "registry_id": "a1", "name": "orders", "pushed": True},
    "remove_app": {"removed": ["d1"], "repositories": []},
    "delete_project": {"removed": ["d1"], "repositories": []},
    "sync_app": APP,
    "checkout": APP,
    "app": {**APP, "branch": "main", "clean": True},
    "gitflow": {"branch": "main", "ok": True, "checked_commits": 0, "problems": []},
    "release": {"current": "1.0.0", "next": "1.1.0", "changelog": "", "dry_run": True},
    "start_branch": FLOW,
    "propose_pr": PR,
    "open_pr": {"number": 1, "url": "https://x/pr/1"},
    "manifest": {"content": "[project]\n"},
    "write_manifest": {},
    "set_cloud": {},
    "add_service": {},
    "commit": {"sha": "abc", "branch": "feature/1", "pushed": True},
    "create_project": CREATED,
    "create_team": CREATED,
    "add_team_member": {"ok": True},
    "assign_project_team": {"ok": True},
    "set_member_role": {"ok": True},
    "matrix": {"projects": [], "clouds": [], "services": []},
}


class FakeRemote:
    server = "https://p.example"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.apps_rows: list[dict] = []
        self.projects_rows: list[dict] = []

    def __getattr__(self, name: str):
        answers = TypeAdapter(get_type_hints(getattr(Remote, name))["return"])

        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

            return answers.validate_python(self.answer(name))

        return method

    def answer(self, name: str) -> Any:
        if name == "whoami":
            return {
                "user": {"email": "me@example.com", "name": "Me"},
                "organization": {"id": "o1", "name": "Acme"},
                "role": "developer",
                "role_label": "Developer",
                "scope": ["read", "write"],
                "permissions": {"app.release": False, "app.configure": True},
                "project": None,
                "app": None,
            }

        if name == "apps" and self.apps_rows:
            return self.apps_rows

        if name == "projects" and self.projects_rows:
            return self.projects_rows

        if name in LISTS:
            return []

        return SHAPES.get(name, {"called": name})


CASES: list[tuple[str, dict[str, Any], str, tuple, dict]] = [
    ("list_apps", {}, "apps", (), {"organization": None}),
    (
        "add_app",
        {"project": "p1", "url": "https://x/y.git"},
        "add_app",
        ("p1", "https://x/y.git", None, None),
        {},
    ),
    (
        "add_app",
        {
            "project": "shop",
            "url": "https://x/y.git",
            "install_type": "web",
            "install_ci": "gitlab",
        },
        "add_app",
        ("p1", "https://x/y.git", {"type": "web", "ci": "gitlab"}, None),
        {},
    ),
    ("remove_app", {"id": "a1"}, "remove_app", ("p1", "d1", False, None), {}),
    (
        "remove_app",
        {"id": "a1", "repository": True},
        "remove_app",
        ("p1", "d1", True, None),
        {},
    ),
    ("delete_project", {"project": "shop"}, "delete_project", ("p1", False, None), {}),
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
    ("deploy", {"id": "a1"}, "deploy", ("a1", None, True, None), {}),
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
        ("a1", "chore: x", True, None, False),
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
        ("a1", "chore: x", True, {"kind": "chore", "code": "7", "slug": None}, True),
        {},
    ),
    ("list_matrix", {}, "matrix", (), {}),
]


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class RemoteToolsTest(TempCase):
    def setUp(self):
        super().setUp()
        from action_platform.mcp.server import MCPServer, REMOTE_INSTRUCTIONS
        from action_platform.mcp.tools import flow, remote as remote_tools

        self.fake = FakeRemote()
        self.fake.projects_rows = [
            {
                "id": "p1",
                "name": "Shop",
                "slug": "shop",
                "apps": [{"id": "d1", "registry_id": "a1", "name": "orders"}],
            }
        ]
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

    def test_whoami_reports_account_role_scope_and_permissions(self):
        who = self.call("whoami", {})

        self.assertEqual(who["server"], "https://p.example")
        self.assertEqual(who["user"]["email"], "me@example.com")
        self.assertEqual(who["organization"]["name"], "Acme")
        self.assertEqual(who["role"], "Developer")
        self.assertEqual(who["scope"], ["read", "write"])
        self.assertFalse(who["can"]["app.release"])
        self.assertTrue(who["can"]["app.configure"])

    def test_directory_tools_call_the_platform(self):
        for tool, method in (
            ("list_organizations", "organizations"),
            ("list_projects", "projects"),
            ("list_teams", "teams"),
            ("list_members", "members"),
        ):
            with self.subTest(tool=tool):
                self.call(tool, {})
                self.assertEqual(self.fake.calls[-1][0], method)

    def test_management_tools_send_their_arguments(self):
        for tool, args, expected in (
            (
                "create_project",
                {"name": "Shop"},
                ("create_project", ("Shop", ""), {"organization": None}),
            ),
            (
                "create_team",
                {"name": "Core", "description": "d", "organization": "acme"},
                ("create_team", ("Core", "d"), {"organization": "acme"}),
            ),
            (
                "add_team_member",
                {"team_id": "t1", "user_id": "u1"},
                ("add_team_member", ("t1", "u1"), {"organization": None}),
            ),
            (
                "assign_project_team",
                {"project_id": "p1", "team_id": "t1"},
                ("assign_project_team", ("p1", "t1"), {"organization": None}),
            ),
            (
                "assign_project_team",
                {"project_id": "p1"},
                ("assign_project_team", ("p1", None), {"organization": None}),
            ),
            (
                "set_member_role",
                {"user_id": "u1", "role": "deployer"},
                ("set_member_role", ("u1", "deployer"), {"organization": None}),
            ),
        ):
            with self.subTest(tool=tool):
                self.call(tool, args)
                self.assertEqual(self.fake.calls[-1], expected)

    def test_current_context_matches_the_checkout_to_an_app(self):
        repo = repo_with_origin(self.tmp_path)
        git(repo, "remote", "set-url", "origin", "git@github.com:Acme/Orders.git")
        self.fake.apps_rows = [
            {"id": "r1", "name": "orders", "url": "https://github.com/acme/orders"}
        ]
        self.fake.projects_rows = [
            {
                "id": "p1",
                "name": "Shop",
                "slug": "shop",
                "team": None,
                "apps": [{"id": "d1", "registry_id": "r1", "name": "orders"}],
            }
        ]

        context = self.call("current_context", {"project": str(repo)})

        self.assertEqual(context["app"]["id"], "r1")
        self.assertEqual(context["project"]["name"], "Shop")
        self.assertEqual(context["organization"]["name"], "Acme")
        self.assertIsNone(context["hint"])

        elsewhere = self.tmp_path / "plain"
        elsewhere.mkdir()
        self.assertIn(
            "not an app",
            self.call("current_context", {"project": str(elsewhere)})["hint"],
        )

    def test_init_app_sends_the_whole_request(self):
        self.call(
            "init_app",
            {
                "project": "shop",
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
        self.assertEqual(args[0], "p1")
        self.assertEqual(
            args[1],
            {
                "type": "web",
                "stack": "python",
                "template": None,
                "name": "Orders",
                "ci": "github",
                "cloud": "docker",
                "template_source": "acme",
                "github_owner": None,
                "push": True,
                "private": True,
            },
        )

    def test_unknown_project_or_app_is_a_readable_error(self):
        for tool, args in (
            ("add_app", {"project": "nope", "url": "https://x/y.git"}),
            ("remove_app", {"id": "zz"}),
        ):
            with self.subTest(tool=tool):
                with self.assertRaises(ToolError) as caught:
                    asyncio.run(self.server.call_tool(tool, args))

                self.assertIn("list_", str(caught.exception))
                self.assertNotIsInstance(caught.exception, UnexpectedToolError)

    def test_project_tools_name_the_organization_of_the_row(self):
        self.fake.projects_rows[0]["organization"] = {"id": "o2", "name": "Other"}

        for tool, args, expected in (
            (
                "add_app",
                {"project": "shop", "url": "https://x/y.git"},
                ("add_app", ("p1", "https://x/y.git", None, "o2"), {}),
            ),
            ("remove_app", {"id": "a1"}, ("remove_app", ("p1", "d1", False, "o2"), {})),
            (
                "delete_project",
                {"project": "p1"},
                ("delete_project", ("p1", False, "o2"), {}),
            ),
        ):
            with self.subTest(tool=tool):
                self.call(tool, args)
                self.assertEqual(self.fake.calls[-1], expected)

    def test_remove_app_answers_with_what_the_platform_removed(self):
        self.assertEqual(
            self.call("remove_app", {"id": "a1"}),
            {"removed": ["d1"], "repositories": []},
        )

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


CONCERNS = {
    "directory": {
        "whoami",
        "list_organizations",
        "list_projects",
        "list_teams",
        "list_members",
        "create_project",
        "create_team",
        "add_team_member",
        "assign_project_team",
        "set_member_role",
    },
    "context": {"current_context"},
    "apps": {
        "list_apps",
        "add_app",
        "remove_app",
        "delete_project",
        "sync_app",
        "app_info",
        "init_app",
    },
    "flow": {
        "gitflow_audit",
        "app_commits",
        "app_branches",
        "app_tags",
        "app_releases",
        "release",
        "start_branch",
        "checkout_branch",
        "propose_pull_request",
        "open_pull_request",
    },
    "configuration": {
        "read_manifest",
        "write_manifest",
        "set_cloud",
        "add_service",
        "commit_changes",
    },
    "deploy": {
        "list_scopes",
        "create_scope",
        "deploy",
        "diagnose",
        "list_deployments",
        "record_deployment",
    },
    "matrix": {"list_matrix"},
}


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class RemotePackageTest(unittest.TestCase):
    def tools(self, register) -> set[str]:
        from action_platform.mcp.server import MCPServer

        server = MCPServer("action-platform")
        register(server, FakeRemote())

        return {t.name for t in asyncio.run(server.list_tools())}

    def test_each_concern_registers_its_own_tools(self):
        from action_platform.mcp.tools import remote as remote_tools

        for module in remote_tools.MODULES:
            name = module.__name__.rsplit(".", 1)[-1]

            with self.subTest(module=name):
                self.assertEqual(self.tools(module.register), CONCERNS[name])

    def test_the_package_registers_every_concern(self):
        from action_platform.mcp.tools import remote as remote_tools

        self.assertEqual(
            self.tools(remote_tools.register), set().union(*CONCERNS.values())
        )


WIRE_PROJECTS = [
    {
        "id": "p1",
        "name": "Shop",
        "slug": "shop",
        "description": None,
        "team": {"id": "t1", "name": "Core"},
        "apps": [{"id": "d1", "name": "orders", "registry_id": "a1"}],
        "organization": {"id": "o2", "name": "Other"},
        "created_at": "2026-09-01T00:00:00",
        "tearing_down": False,
    }
]


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class RemoteToolsOverTheWireTest(TempCase):
    def setUp(self):
        super().setUp()
        from action_platform.mcp.server import MCPServer, REMOTE_INSTRUCTIONS
        from action_platform.mcp.tools import remote as remote_tools
        from action_platform.remote import client

        self.sent: list[tuple[str, str, Any, Any]] = []

        def fake_request(method, url, body=None, token=None, **kwargs):
            self.sent.append((method, url, body, kwargs.get("organization")))
            path = url.split("?")[0]

            if path.endswith("/projects"):
                return WIRE_PROJECTS

            if path.endswith("/scopes"):
                return {"items": [], "kinds": ["web"], "criticalities": ["low"]}

            return {"removed": ["d1"], "repositories": [], "job": "j1"}

        self.patch(client, "_request", fake_request)
        self.server = MCPServer("action-platform", instructions=REMOTE_INSTRUCTIONS)
        remote_tools.register(self.server, Remote("https://p.example", "tok"))

    def call(self, tool: str, args: dict[str, Any]):
        result = asyncio.run(self.server.call_tool(tool, args))

        return result.structured_content.get("result", result.structured_content)

    def test_tools_find_rows_through_the_real_client(self):
        self.assertEqual(
            self.call("remove_app", {"id": "a1"}),
            {"removed": ["d1"], "repositories": [], "job": "j1"},
        )
        self.assertEqual(
            self.sent[-1][:2],
            ("DELETE", "https://p.example/api/v1/projects/p1/apps/d1"),
        )
        self.assertEqual(self.sent[-1][3], "o2")

        self.call("list_scopes", {"id": "a1"})
        self.assertEqual(
            self.sent[-1][1], "https://p.example/api/v1/projects/p1/apps/d1/scopes"
        )

    def test_list_projects_keeps_what_the_platform_sent(self):
        (row,) = self.call("list_projects", {"organization": "other"})

        self.assertEqual(row["organization"], {"id": "o2", "name": "Other"})
        self.assertEqual(row["apps"][0]["registry_id"], "a1")
        self.assertIs(row["tearing_down"], False)
        self.assertEqual(self.sent[-1][3], "other")
