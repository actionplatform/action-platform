"""How a template turns into files: cookiecutter for rendered templates, a plain copy for overlays without one.

Rendering runs in a process of its own (`sandbox`), in a temporary directory, with an environment that carries no credentials and a sandboxed Jinja. Templates from the official repository or an installed plugin are trusted to run their hooks; any other source is not: hooks, Jinja extensions and nested templates are refused, and no template may hold a symlink that leaves its directory.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from action_platform.core import extensions
from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.sources import LocalTemplateStore

TIMEOUT = 300
PASSED_ENV = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
HOOKS = ("pre_prompt", "pre_gen_project", "post_gen_project")
UNTRUSTED_KEYS = ("_extensions", "_jinja2_env_vars", "template", "templates")


def trusted_roots() -> list[Path]:
    """The official templates repository and the plugins' overlay directories: the only templates whose hooks run."""
    config = LocalTemplateStore().config
    roots = [config.cache]

    if config.dir:
        roots.append(Path(config.dir).expanduser())

    roots.extend(root for _, root in extensions.current().overlay_roots())

    return [root.resolve() for root in roots]


def is_trusted(repo: Path) -> bool:
    return repo.resolve() in trusted_roots()


def check_tree(root: Path) -> None:
    """Refuse a symlink that points outside `root`, or at a directory: a template must not reach files it does not hold."""
    base = root.resolve()

    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]

        for name in [*dirs, *files]:
            path = Path(current) / name

            if not path.is_symlink():
                continue

            target = path.resolve()

            if not target.is_relative_to(base) or not target.is_file():
                raise TemplateError(
                    f"{path.relative_to(root)} is a symlink out of the template; refused"
                )


def check_untrusted(template: Path) -> None:
    """A template from a custom source renders text only: no hooks, no Jinja extensions, no nested templates."""
    hooks = template / "hooks"

    if hooks.is_dir() and any(p.stem in HOOKS for p in hooks.iterdir()):
        raise TemplateError(
            "hooks are not run for templates outside the official repository; refused"
        )

    config = template / "cookiecutter.json"

    try:
        data = json.loads(config.read_text())
    except (OSError, ValueError) as e:
        raise TemplateError(f"cannot read {config.name}: {e}") from e

    refused = sorted(key for key in UNTRUSTED_KEYS if key in data)

    if refused:
        raise TemplateError(
            f"{', '.join(refused)} not allowed in templates outside the official repository"
        )


def isolated_env(work: Path) -> dict[str, str]:
    """The renderer's whole environment: locale and PATH, a HOME and TMPDIR of its own — no tokens, no database, no secrets."""
    env = {key: os.environ[key] for key in PASSED_ENV if key in os.environ}
    env["HOME"] = str(work / "home")
    env["TMPDIR"] = str(work / "tmp")

    return env


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
        source = repo / directory

        if not source.is_dir():
            raise TemplateError(f"no template at {directory or repo}")

        check_tree(source)
        trusted = is_trusted(repo)

        with tempfile.TemporaryDirectory(prefix="ap-render-") as tmp:
            work = Path(tmp)
            template = work / "template"
            shutil.copytree(source, template)

            if not trusted:
                check_untrusted(template)

            for name in ("out", "home", "tmp"):
                (work / name).mkdir()

            rendered = self._run(work, template, context, trusted)
            target = output / rendered.name

            if target.exists() and not overwrite:
                raise TemplateError(f'"{target}" directory already exists')

            output.mkdir(parents=True, exist_ok=True)
            shutil.copytree(rendered, target, symlinks=True, dirs_exist_ok=True)

        return target

    @staticmethod
    def _run(work: Path, template: Path, context: dict, trusted: bool) -> Path:
        result = work / "result.json"
        request = {
            "template": str(template),
            "output": str(work / "out"),
            "context": context,
            "trusted": trusted,
            "result": str(result),
        }

        try:
            process = subprocess.run(
                [sys.executable, "-I", "-m", "action_platform.core.scaffold.sandbox"],
                input=json.dumps(request),
                cwd=work,
                env=isolated_env(work),
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise TemplateError(f"rendering took longer than {TIMEOUT}s") from e

        try:
            outcome = json.loads(result.read_text())
        except (OSError, ValueError) as e:
            last = process.stderr.strip().splitlines()[-1:] or ["no output"]
            raise TemplateError(
                f"the template renderer stopped without a result: {last[0]}"
            ) from e

        if "error" in outcome:
            raise TemplateError(outcome["error"])

        return Path(outcome["project"])

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
        check_tree(source)

        for item in source.rglob("*"):
            if not item.is_file():
                continue

            target = project / item.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
