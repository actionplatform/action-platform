"""action_platform.core.scaffold.renderer — templates turned into files, without platform.toml or git."""

from __future__ import annotations

import json

from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.renderer import TemplateRenderer
from tests.support import TempCase, template_repo


class RenderTest(TempCase):
    def test_renders_a_leaf_into_the_output(self):
        repo = template_repo(self.tmp_path / "templates", rendered=True)

        project = TemplateRenderer().render(
            repo,
            "projects/web/python/fastapi",
            self.tmp_path / "out",
            {"project_name": "Demo App"},
        )

        self.assertEqual(project, self.tmp_path / "out" / "demo-app")
        self.assertIn("# Demo App", (project / "README.md").read_text())
        self.assertTrue((project / "demo_app" / "__init__.py").exists())
        self.assertFalse((project / ".git").exists())

    def test_a_cookiecutter_failure_is_a_template_error(self):
        repo = template_repo(self.tmp_path / "templates")

        with self.assertRaises(TemplateError):
            TemplateRenderer().render(repo, "projects/missing", self.tmp_path, {})


class OverlayTest(TempCase):
    def test_renders_with_the_project_name_as_slug_over_the_project(self):
        overlay = self.tmp_path / "templates" / "cloud" / "box"
        (overlay / "{{cookiecutter.project_slug}}").mkdir(parents=True)
        (overlay / "cookiecutter.json").write_text(
            json.dumps({"project_name": "x", "project_slug": "x"})
        )
        (overlay / "{{cookiecutter.project_slug}}" / "DEPLOY.md").write_text(
            "# {{ cookiecutter.project_slug }}\n"
        )
        project = self.tmp_path / "registry-id"
        project.mkdir()

        TemplateRenderer().overlay(
            self.tmp_path / "templates", "cloud/box", project, {"project_name": "shop"}
        )

        self.assertEqual((project / "DEPLOY.md").read_text(), "# shop\n")

    def test_copy_lays_every_file_over_the_project(self):
        source = self.tmp_path / "overlay"
        (source / "deploy").mkdir(parents=True)
        (source / "deploy" / "run.sh").write_text("echo hi\n")
        project = self.tmp_path / "project"
        (project / "deploy").mkdir(parents=True)
        (project / "deploy" / "run.sh").write_text("old\n")
        (project / "keep.txt").write_text("kept\n")

        TemplateRenderer.copy(source, project)

        self.assertEqual((project / "deploy" / "run.sh").read_text(), "echo hi\n")
        self.assertEqual((project / "keep.txt").read_text(), "kept\n")
