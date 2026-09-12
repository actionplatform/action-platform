"""Run cookiecutter for project leaves, cloud overlays and services; keep platform.toml in sync."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

from action_platform.core import git
from action_platform.core.config import Config
from action_platform.core.exception import TemplateError
from action_platform.core.templates import Cloud, Leaf, Service
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

    _cookiecutter(
        repo,
        cloud.directory,
        project.parent,
        {
            "project_name": meta.get("name", project.name),
            "project_slug": project.name,
            "language": language,
            "type": type_,
            "ci": meta.get("ci", "github"),
        },
        overwrite=True,
    )

    _write_deploy_target(project / settings.CONFIG_FILE, cloud.name)

    return project


def apply_service(
    repo: Path, service: Service, project: Path, provider: str | None = None
) -> Path:
    """Add `services/<name>/` to the project and record it under [services] in platform.toml."""
    meta = read_platform(project)
    provider = provider or (service.providers[0] if service.providers else "")

    if service.providers and provider not in service.providers:
        raise TemplateError(
            f"service {service.name} has no provider {provider!r} "
            f"(available: {', '.join(service.providers)})"
        )

    existing = project / "services" / service.name
    if existing.exists():
        shutil.rmtree(existing)

    _cookiecutter(
        repo,
        service.directory,
        project.parent,
        {
            "project_name": meta.get("name", project.name),
            "project_slug": project.name,
            "provider": provider,
        },
        overwrite=True,
    )

    _write_service(project / settings.CONFIG_FILE, service.name, provider)

    return project


def push_project(project: Path, private: bool = False, branch: str = "main") -> str:
    """git init, first commit, create the remote via [source_host], push.

    No secrets are written: the deploy workflow needs them, but which ones and
    from where is the operator's call — DEPLOY.md in the project lists them.
    """
    config = Config.from_toml(project / settings.CONFIG_FILE)

    if config.source_host is None:
        raise TemplateError("platform.toml has no [source_host]; cannot push")

    meta = read_platform(project)

    if not (project / ".git").exists():
        git.init(project, branch=branch)

    git.add_all(project)

    if not git.is_clean(cwd=project):
        git.run(
            ["commit", "-q", "-m", "chore: bootstrap project from action-platform"],
            cwd=project,
        )

    url = config.source_host.create_repository(
        config.source_host.repo,
        description=meta.get("description", ""),
        private=private,
    )

    if not git.remote_url(cwd=project):
        git.add_remote(url, project)

    git.push_upstream(branch, project)

    return url


def read_platform(project: Path) -> dict:
    path = project / settings.CONFIG_FILE

    if not path.exists():
        raise TemplateError(f"{settings.CONFIG_FILE} not found in {project}")

    data = tomllib.loads(path.read_text())

    return data.get("project", {})


def _write_deploy_target(path: Path, target: str) -> None:
    text = path.read_text()
    line = f'target = "{target}"'

    if "[deploy]" not in text:
        path.write_text(text.rstrip("\n") + f"\n\n[deploy]\n{line}\n")
        return

    lines = text.splitlines()

    for i, current in enumerate(lines):
        if current.strip().startswith("target ="):
            lines[i] = line
            break
    else:
        lines.insert(lines.index("[deploy]") + 1, line)

    path.write_text("\n".join(lines) + "\n")


def _write_service(path: Path, name: str, provider: str) -> None:
    text = path.read_text()
    line = f'{name} = "{provider}"'

    if "[services]" not in text:
        path.write_text(text.rstrip("\n") + f"\n\n[services]\n{line}\n")
        return

    lines = text.splitlines()
    start = lines.index("[services]")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("[")),
        len(lines),
    )

    for i in range(start + 1, end):
        if lines[i].split("=")[0].strip() == name:
            lines[i] = line
            break
    else:
        lines.insert(end, line)

    path.write_text("\n".join(lines) + "\n")


def _cookiecutter(
    repo: Path, directory: str, output: Path, extra: dict, overwrite: bool = False
) -> Path:
    from cookiecutter.exceptions import CookiecutterException
    from cookiecutter.main import cookiecutter

    try:
        result = cookiecutter(
            str(repo),
            directory=directory,
            no_input=True,
            extra_context=extra,
            output_dir=str(output),
            overwrite_if_exists=overwrite,
        )
    except CookiecutterException as e:
        raise TemplateError(str(e)) from e

    return Path(result)
