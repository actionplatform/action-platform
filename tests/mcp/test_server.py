"""action_platform.mcp.server — the local tool surface and its read-only tools."""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from tests.mcp.support import HAS_MCP, McpCase
from tests.support import TempCase, git, install_templates

if HAS_MCP:
    from action_platform.mcp import server


PLUGIN_PREFIXES = ("example_", "aws_lambda_")


class ToolSurfaceTest(McpCase):
    def test_tools_exposed(self):
        self.assertEqual(
            {name for name in self.tools() if not name.startswith(PLUGIN_PREFIXES)},
            {
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
                "propose_pull_request",
                "open_pull_request",
                "list_scopes",
                "readiness",
                "job_logs",
                "record_deployment",
            },
        )

    def test_cloud_and_service_name_what_the_matrix_offers(self):
        tools = self.tools()

        self.assertIn(
            "docker",
            tools["cloud_set"].input_schema["properties"]["cloud"]["description"],
        )
        self.assertIn(
            "postgres",
            tools["service_add"].input_schema["properties"]["service"]["description"],
        )

    def test_a_plugin_cloud_joins_the_cloud_description(self):
        import json

        from action_platform.core import extensions
        from action_platform.mcp import build

        overlays = self.tmp_path / "overlays"
        overlays.mkdir()
        (overlays / "index.json").write_text(
            json.dumps({"clouds": [{"id": "dokploy", "description": "Dokploy"}]})
        )
        plugins = mock.Mock()
        plugins.overlay_roots.return_value = [("dokploy", overlays)]

        with mock.patch.object(extensions, "current", return_value=plugins):
            server_ = build()

        tools = {t.name: t for t in asyncio.run(server_.list_tools())}
        description = tools["cloud_set"].input_schema["properties"]["cloud"][
            "description"
        ]

        self.assertIn("dokploy", description)
        self.assertIn("docker", description)

    def test_without_a_matrix_on_this_machine_list_matrix_is_named(self):
        from action_platform.mcp import build

        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.tmp_path / "missing"))
        tools = {t.name: t for t in asyncio.run(build().list_tools())}

        self.assertIn(
            "list_matrix",
            tools["service_add"].input_schema["properties"]["service"]["description"],
        )

    def test_irreversible_tools_are_flagged(self):
        tools = self.tools()

        self.assertTrue(tools["list_matrix"].annotations.read_only_hint)
        self.assertTrue(tools["project_info"].annotations.read_only_hint)
        self.assertTrue(tools["push_project"].annotations.open_world_hint)
        self.assertTrue(tools["rollback"].annotations.destructive_hint)
        self.assertFalse(tools["init_project"].annotations.destructive_hint)
        self.assertTrue(tools["start_branch"].annotations.open_world_hint)
        self.assertTrue(tools["open_pull_request"].annotations.open_world_hint)
        self.assertTrue(tools["propose_pull_request"].annotations.read_only_hint)
        self.assertTrue(tools["gitflow_audit"].annotations.read_only_hint)
        self.assertTrue(tools["gitflow_rules"].annotations.read_only_hint)
        self.assertFalse(tools["install_platform"].annotations.open_world_hint)
        self.assertFalse(tools["install_hooks"].annotations.destructive_hint)
        self.assertTrue(tools["list_scopes"].annotations.read_only_hint)
        self.assertTrue(tools["readiness"].annotations.read_only_hint)
        self.assertTrue(tools["job_logs"].annotations.read_only_hint)
        self.assertTrue(tools["record_deployment"].annotations.open_world_hint)

    def test_dry_run_is_the_default_where_it_matters(self):
        tools = self.tools()

        for name in ("release", "deploy", "install_platform"):
            self.assertIs(
                tools[name].input_schema["properties"]["dry_run"]["default"], True
            )

    def test_instructions_warn_before_reaching_out(self):
        self.assertIn("push_project", self.server.instructions)
        self.assertIn("dry_run", self.server.instructions)


class ReadOnlyToolsTest(McpCase):
    def test_list_matrix(self):
        data = self.call("list_matrix")

        self.assertEqual(data["projects"][0]["template"], "fastapi")
        self.assertEqual(data["clouds"][0]["name"], "docker")
        self.assertEqual(data["services"][0]["providers"], ["docker"])

    def test_project_info(self):
        project = self.tmp_path / "p"
        project.mkdir()
        (project / "platform.toml").write_text(
            '[project]\nname = "x"\ntype = "web"\nlanguage = "python"\n[source_host]\nkind = "github"\nrepo = "acme/x"\n'
        )

        data = self.call("project_info", project=str(project))

        self.assertEqual(data["type"], "web")
        self.assertEqual(data["github_owner"], "acme")

    def test_list_scopes_reads_platform_toml(self):
        project = self.tmp_path / "p"
        project.mkdir()
        (project / "platform.toml").write_text(
            '[project]\nname = "x"\n\n[[scopes]]\nname = "dev"\ncriticality = "test"\n\n'
            '[[scopes]]\nname = "prod"\nkind = "job"\ncriticality = "high"\n'
        )

        data = self.call("list_scopes", project=str(project))

        self.assertEqual(
            data["items"],
            [
                {"name": "dev", "kind": "web", "criticality": "test"},
                {"name": "prod", "kind": "job", "criticality": "high"},
            ],
        )
        self.assertIn("critical", data["criticalities"])

    def test_readiness_answers_with_a_verdict_and_the_checks(self):
        from action_platform.core.context import Check
        from action_platform.core.facade import ActionPlatform

        project = self.tmp_path / "p"
        project.mkdir()
        (project / "platform.toml").write_text('[project]\nname = "x"\n')
        checks = [
            Check("aws.credentials", True, "ok"),
            Check("aws.permissions", False, "may not deploy", fix="grant it"),
        ]

        with mock.patch.object(
            ActionPlatform, "check_readiness", return_value=checks
        ) as check:
            data = self.call(
                "readiness", project=str(project), scope="prod", version="1.2.3"
            )

        check.assert_called_once_with("prod", version="1.2.3", target=None)
        self.assertEqual(
            (data["stage"], data["verdict"], data["ok"]), ("prod", "blocked", False)
        )
        self.assertEqual(data["checks"][1]["fix"], "grant it")

        with mock.patch.object(
            ActionPlatform,
            "check_readiness",
            return_value=[Check("lockfile", False, "none", severity="warning")],
        ):
            data = self.call("readiness", project=str(project), scope="prod")

        self.assertEqual(data["verdict"], "ok")

    def test_gitflow_rules(self):
        rules = self.call("gitflow_rules")

        self.assertIn("feature", rules["kinds"])
        self.assertEqual(rules["protected"], ["develop", "main", "master"])
        self.assertIn("hotfix", rules["base"]["default branch (main/master)"])

    def test_install_platform_dry_run(self):
        install_templates(self.tmp_path)
        repo = self.tmp_path / "existing"
        repo.mkdir()
        git(repo, "init", "-q")
        (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")

        data = self.call("install_platform", project=str(repo))

        self.assertTrue(data["dry_run"])
        self.assertIn("platform.toml", data["created"])
        self.assertFalse((repo / "platform.toml").exists())

    def test_gitflow_audit_reports_problems(self):
        repo = self.tmp_path / "flow"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "commit", "-q", "--allow-empty", "-m", "chore: bootstrap")
        git(repo, "tag", "v0.1.0")
        git(repo, "checkout", "-qb", "wip")
        git(repo, "commit", "-q", "--allow-empty", "-m", "did stuff")

        data = self.call("gitflow_audit", project=str(repo), since="v0.1.0")

        self.assertFalse(data["ok"])
        self.assertTrue(any("not git-flow" in p for p in data["problems"]))
        self.assertTrue(any("not a conventional commit" in p for p in data["problems"]))


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class EntryPointTest(TempCase):
    def test_main_bootstraps_as_mcp_before_building_the_server(self):
        calls = []
        server_ = mock.Mock()
        self.patch(server, "bootstrap", lambda component: calls.append(component))
        self.patch(
            server, "build", lambda remote: calls.append(("build", remote)) or server_
        )

        server.main([])

        self.assertEqual(calls, ["mcp", ("build", None)])
        server_.run.assert_called_once_with()
