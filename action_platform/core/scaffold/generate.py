"""Run cookiecutter for project leaves, cloud overlays and services; keep platform.toml in sync."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from action_platform.core.config import Config
from action_platform.core.exception import TemplateError
from action_platform.core.flow import git, gitflow
from action_platform.core.manifest import (
    read_platform,
    write_deploy_target,
    write_service,
)
from action_platform.core.scaffold.templates import Cloud, Leaf, Service
from action_platform.settings import settings


def generate_project(
    repo: Path,
    leaf: Leaf,
    name: str,
    ci: str | None,
    output: Path,
    extra: dict | None = None,
) -> Path:
    """Render `leaf` into `output`/<slug>. `extra` overrides cookiecutter defaults (description, package_name, github_owner…)."""
    context = {**(extra or {}), "project_name": name}

    if ci is not None:
        context["ci"] = ci

    return _cookiecutter(repo, leaf.directory, output, context)


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
            "github_owner": meta.get("github_owner", "actionplatform"),
            "language": language,
            "type": type_,
            "ci": meta.get("ci", "github"),
        },
        overwrite=True,
    )

    write_deploy_target(project / settings.CONFIG_FILE, cloud.name)

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
            "github_owner": meta.get("github_owner", "actionplatform"),
            "provider": provider,
        },
        overwrite=True,
    )

    write_service(project / settings.CONFIG_FILE, service.name, provider)

    return project


def push_project(
    project: Path,
    private: bool = False,
    branch: str = "main",
    credentials: "SourceCredentialsLike | None" = None,
) -> str:
    """git init, first commit, create the remote via [source_host], push.

    No secrets are written: the deploy workflow needs them, but which ones and
    from where is the operator's call — DEPLOY.md in the project lists them.
    `credentials` (kind, token, username, base_url) override the environment's.
    """
    config = Config.from_toml(project / settings.CONFIG_FILE)

    if credentials is not None and config.source_host is not None:
        from action_platform.providers.source import build_source_host

        config.source_host = build_source_host(
            credentials.kind,
            config.source_host.repo,
            base_url=credentials.base_url,
            token=credentials.token,
            username=credentials.username,
        )

    if config.source_host is None:
        raise TemplateError("platform.toml has no [source_host]; cannot push")

    meta = read_platform(project)

    if not (project / ".git").exists():
        git.init(project, branch=branch)

    gitflow.install_hooks(project)
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

    try:
        git.push_upstream(branch, project)
    except subprocess.CalledProcessError as e:
        raise TemplateError(
            f"push failed: {e.stderr.strip() if e.stderr else e}"
        ) from e

    return url


class SourceCredentialsLike(Protocol):
    kind: str
    token: str
    username: str | None
    base_url: str | None


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
