"""Run cookiecutter for project leaves and cloud overlays; keep platform.toml in sync."""

from __future__ import annotations

import tomllib
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.core.templates import Cloud, Leaf
from action_platform.settings import settings


def generate_project(
    repo: Path, leaf: Leaf, name: str, ci: str | None, output: Path
) -> Path:
    extra = {"project_name": name}
    if ci is not None:
        extra["ci"] = ci
    return _cookiecutter(repo, leaf.directory, output, extra)


def apply_cloud(repo: Path, cloud: Cloud, project: Path) -> Path:
    """Overlay `cloud` onto an existing project directory and record it in platform.toml."""
    meta = read_platform(project)
    type_ = meta.get("type", "")
    language = meta.get("language", "")
    if not cloud.supports(type_, language):
        raise TemplateError(
            f"cloud {cloud.name} does not support {type_}/{language} "
            f"(types: {cloud.types or 'any'}, languages: {cloud.languages or 'any'})"
        )
    ci = meta.get("ci", "github")
    _cookiecutter(
        repo,
        cloud.directory,
        project.parent,
        {
            "project_name": meta.get("name", project.name),
            "project_slug": project.name,
            "language": language,
            "type": type_,
            "ci": ci,
        },
        overwrite=True,
    )
    _write_deploy_target(project / settings.CONFIG_FILE, cloud.name)
    return project


def read_platform(project: Path) -> dict:
    path = project / settings.CONFIG_FILE
    if not path.exists():
        raise TemplateError(f"{settings.CONFIG_FILE} not found in {project}")
    data = tomllib.loads(path.read_text())
    return data.get("project", {})


def _write_deploy_target(path: Path, target: str) -> None:
    text = path.read_text()
    if "[deploy]" in text:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("target ="):
                lines[i] = f'target = "{target}"'
                break
        else:
            idx = lines.index("[deploy]") + 1
            lines.insert(idx, f'target = "{target}"')
        text = "\n".join(lines) + "\n"
    else:
        text = text.rstrip("\n") + f'\n\n[deploy]\ntarget = "{target}"\n'
    path.write_text(text)


def _cookiecutter(
    repo: Path, directory: str, output: Path, extra: dict, overwrite: bool = False
) -> Path:
    from cookiecutter.exceptions import CookiecutterException
    from cookiecutter.main import cookiecutter

    try:
        return Path(
            cookiecutter(
                str(repo),
                directory=directory,
                no_input=True,
                extra_context=extra,
                output_dir=str(output),
                overwrite_if_exists=overwrite,
            )
        )
    except CookiecutterException as e:
        raise TemplateError(str(e)) from e
