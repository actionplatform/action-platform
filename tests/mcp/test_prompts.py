"""action_platform.mcp.prompts — each prompt names its tools in order and stops before anything irreversible."""

from __future__ import annotations

import asyncio

from tests.mcp.support import McpCase


class PromptsTest(McpCase):
    def test_prompts_exposed(self):
        names = {p.name for p in asyncio.run(self.server.list_prompts())}

        self.assertEqual(
            names,
            {
                "new_service",
                "ship_feature",
                "cut_release",
                "deploy_project",
                "adopt_repository",
                "fix_gitflow",
            },
        )

    def test_new_service_pushes_last_and_only_on_yes(self):
        text = self.prompt(
            "new_service", name="orders", stack="python", cloud="aws/lambda"
        )

        self.assertLess(text.index("list_matrix"), text.index("init_project"))
        self.assertLess(text.index("init_project"), text.index("push_project"))
        self.assertIn("Never call push_project in the same turn", text)

    def test_ship_feature_audits_before_pull_request(self):
        text = self.prompt("ship_feature", issue="42")

        self.assertLess(text.index("start_branch"), text.index("gitflow_audit"))
        self.assertLess(text.index("gitflow_audit"), text.index("propose_pull_request"))
        self.assertLess(
            text.index("propose_pull_request"), text.index("open_pull_request")
        )

    def test_cut_release_previews_and_explains_rc(self):
        text = self.prompt("cut_release", level="minor")

        self.assertIn("dry_run=true", text)
        self.assertIn("dry_run=false", text)
        self.assertIn("rc.N", text)

    def test_deploy_preflights_then_confirms(self):
        text = self.prompt("deploy_project")

        self.assertLess(text.index("dry_run=true"), text.index("wait for a yes"))
        self.assertLess(text.index("wait for a yes"), text.index("dry_run=false"))
        self.assertIn("diagnose", text)
