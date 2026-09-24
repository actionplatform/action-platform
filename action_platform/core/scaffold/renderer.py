"""How a template turns into files: cookiecutter for rendered templates, a plain copy for overlays without one."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter

from action_platform.core.exception import TemplateError


class TemplateRenderer:
    """Renders a directory of a template repository; knows nothing of platform.toml or git."""

    def render(
        self,
        repo: Path,
        directory: str,
        output: Path,
        context: dict,
        overwrite: bool = False,
    ) -> Path:
        """Run cookiecutter on `repo`/`directory` into `output`; the rendered project's path."""
        try:
            result = cookiecutter(
                str(repo),
                directory=directory,
                no_input=True,
                extra_context=context,
                output_dir=str(output),
                overwrite_if_exists=overwrite,
            )
        except CookiecutterException as e:
            raise TemplateError(str(e)) from e

        return Path(result)

    def overlay(self, repo: Path, directory: str, project: Path, context: dict) -> None:
        """Render a cookiecutter overlay with the project's own name as `project_slug` — not the directory it happens to live in, which on the platform is a registry id — and lay the files over the project."""
        slug = context["project_name"]

        with tempfile.TemporaryDirectory(prefix="ap-overlay-") as tmp:
            rendered = self.render(
                repo, directory, Path(tmp), {**context, "project_slug": slug}
            )
            self.copy(rendered, project)

    @staticmethod
    def copy(source: Path, project: Path) -> None:
        """A plain overlay — no cookiecutter.json — is copied as it is, file over file."""
        for item in source.rglob("*"):
            if not item.is_file():
                continue

            target = project / item.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
