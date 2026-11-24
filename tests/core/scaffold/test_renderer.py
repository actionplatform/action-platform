"""action_platform.core.scaffold.renderer — templates turned into files, without platform.toml or git."""

from __future__ import annotations

import json
import os

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


SECRETS = {
    "AP_AUTH_SECRET": "auth-secret-value",
    "AP_DATABASE_URL": "postgresql://user:pw@db/ap",
    "ACTION_PLATFORM_GITHUB_TOKEN": "ghp_token",
}


class IsolationTest(TempCase):
    def setUp(self):
        super().setUp()

        for name, value in SECRETS.items():
            self.setenv(name, value)

        self.delenv("ACTION_PLATFORM_TEMPLATES")
        self.repo = template_repo(self.tmp_path / "templates", rendered=True)
        self.leaf = self.repo / "projects/web/python/fastapi"
        self.slug = self.leaf / "{{cookiecutter.project_slug}}"
        self.out = self.tmp_path / "out"

    def render(self, **context):
        return TemplateRenderer().render(
            self.repo,
            "projects/web/python/fastapi",
            self.out,
            {"project_name": "Demo", **context},
        )

    def add_hook(self):
        hooks = self.leaf / "hooks"
        hooks.mkdir()
        (hooks / "post_gen_project.py").write_text(
            "import json, os\n"
            "from pathlib import Path\n"
            "Path('env.json').write_text(json.dumps(dict(os.environ)))\n"
        )

    def test_the_official_repository_runs_its_hooks_without_the_api_s_secrets(self):
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.repo))
        self.add_hook()

        project = self.render()
        env = json.loads((project / "env.json").read_text())

        for name, value in SECRETS.items():
            self.assertNotIn(name, env)
            self.assertNotIn(value, json.dumps(env))

        self.assertNotEqual(env["HOME"], os.environ.get("HOME"))
        self.assertIn("# Demo", (project / "README.md").read_text())

    def test_a_custom_template_cannot_read_the_environment_through_jinja(self):
        (self.slug / "leak.txt").write_text(
            "{{ cycler.__init__.__globals__.os.environ.AP_AUTH_SECRET }}"
        )

        with self.assertRaisesRegex(TemplateError, "unsafe"):
            self.render()

        self.assertFalse(self.out.exists())

    def test_user_input_is_rendered_without_access_to_the_process(self):
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.repo))

        with self.assertRaisesRegex(TemplateError, "unsafe"):
            self.render(description="{{ lipsum.__globals__.os.environ }}")

    def test_a_custom_template_s_hook_is_refused(self):
        self.add_hook()

        with self.assertRaisesRegex(TemplateError, "hooks"):
            self.render()

        self.assertFalse(self.out.exists())

    def test_a_custom_template_cannot_load_jinja_extensions(self):
        config = self.leaf / "cookiecutter.json"
        data = json.loads(config.read_text())
        data["_extensions"] = ["local_extensions.Leak"]
        config.write_text(json.dumps(data))
        (self.leaf / "local_extensions.py").write_text("raise SystemExit(3)\n")

        with self.assertRaisesRegex(TemplateError, "_extensions"):
            self.render()

    def test_an_include_of_an_absolute_path_fails(self):
        (self.slug / "passwd.txt").write_text('{% include "/etc/passwd" %}')

        with self.assertRaises(TemplateError):
            self.render()

        self.assertFalse(self.out.exists())

    def test_an_include_out_of_the_template_directory_fails(self):
        other = self.tmp_path / "workspaces" / "other-org"
        other.mkdir(parents=True)
        (other / "secret.txt").write_text("other organization data")
        (self.slug / "other.txt").write_text(
            '{% include "../../../../../workspaces/other-org/secret.txt" %}'
        )

        with self.assertRaises(TemplateError):
            self.render()

        self.assertFalse(self.out.exists())

    def test_a_symlink_to_another_organization_s_files_is_refused(self):
        other = self.tmp_path / "workspaces" / "other-org"
        other.mkdir(parents=True)
        (other / "secret.txt").write_text("other organization data")
        (self.slug / "secret.txt").symlink_to(other / "secret.txt")

        with self.assertRaisesRegex(TemplateError, "symlink"):
            self.render()

    def test_a_symlink_to_a_system_file_is_refused(self):
        (self.slug / "passwd").symlink_to("/etc/passwd")

        with self.assertRaisesRegex(TemplateError, "symlink"):
            self.render()

    def test_a_symlink_inside_the_template_is_followed(self):
        (self.slug / "COPY.md").symlink_to(self.slug / "README.md")

        project = self.render()

        self.assertIn("# Demo", (project / "COPY.md").read_text())

    def test_a_plain_overlay_with_an_escaping_symlink_is_refused(self):
        source = self.tmp_path / "overlay"
        source.mkdir()
        (source / "passwd").symlink_to("/etc/passwd")
        project = self.tmp_path / "project"
        project.mkdir()

        with self.assertRaisesRegex(TemplateError, "symlink"):
            TemplateRenderer.copy(source, project)

        self.assertFalse((project / "passwd").exists())
