"""action_platform.mcp.server — the local tool surface and its read-only tools."""

from __future__ import annotations

from tests.mcp.support import McpCase
from tests.support import git, install_templates


class ToolSurfaceTest(McpCase):
    def test_tools_exposed(self):
        self.assertEqual(
            set(self.tools()),
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
            },
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
