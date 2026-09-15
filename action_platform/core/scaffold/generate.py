"""Run cookiecutter for project leaves, cloud overlays and services; keep platform.toml in sync."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter

from action_platform.core.wiring import slot, wired
from action_platform.core.config import Config
from action_platform.core.exception import TemplateError
from action_platform.core.flow.repository import Repository
from action_platform.core.manifest import Manifest, check_owner, toml_str
from action_platform.core.scaffold.templates import Cloud, Leaf, Service
from action_platform.providers.source import build_source_host
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

    if leaf.plain:
        return _copy_repository(repo, leaf, name, ci, output, context)

    return _cookiecutter(repo, leaf.directory, output, context)


def _copy_repository(
    repo: Path, leaf: Leaf, name: str, ci: str | None, output: Path, context: dict
) -> Path:
    """Copy a plain repository as the new project and make sure it carries platform.toml, hooks and CI."""
    slug = _slugify(name)
    target = output / slug

    if target.exists():
        raise TemplateError(f"{target} already exists")

    shutil.copytree(repo, target, ignore=shutil.ignore_patterns(".git"))
    manifest = target / settings.CONFIG_FILE

    if not (target / settings.LAST_VERSION_FILE).exists():
        (target / settings.LAST_VERSION_FILE).write_text("0.0.0\n")

    if manifest.exists():
        text = manifest.read_text()
        manifest.write_text(
            re.sub(
                r'(?m)^name\s*=\s*".*"$',
                lambda _: f"name = {toml_str(slug)}",
                text,
                count=1,
            )
        )
        _replace_owner(manifest, context.get("github_owner"))
        return target

    Repository.init(target, branch="main")

    if leaf.stack:
        wired.installer(target, type_=leaf.type, language=leaf.stack, ci=ci).apply()
    else:
        (target / settings.CONFIG_FILE).write_text(
            f'[project]\nname = "{slug}"\ntype = "{leaf.type}"\nci = "{ci or "github"}"\n'
            '\n[release]\nstrategy = "semver"\nchangelog = "conventional"\n'
        )
        (target / settings.LAST_VERSION_FILE).write_text("0.0.0\n")

    shutil.rmtree(target / ".git", ignore_errors=True)
    _replace_owner(target / settings.CONFIG_FILE, context.get("github_owner"))

    if context.get("description"):
        text = (target / settings.CONFIG_FILE).read_text()
        (target / settings.CONFIG_FILE).write_text(
            text.replace(
                "[project]\n",
                f"[project]\ndescription = {toml_str(str(context['description']))}\n",
                1,
            )
        )

    return target


def _replace_owner(manifest: Path, owner: str | None) -> None:
    if not owner or not manifest.exists():
        return

    check_owner(owner)
    text = manifest.read_text()

    if "[source_host]" in text:
        manifest.write_text(
            re.sub(
                r'(?m)^repo\s*=\s*"[^/"]+/',
                lambda _: f'repo = "{owner}/',
                text,
                count=1,
            )
        )


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def apply_cloud(repo: Path, cloud: Cloud, project: Path) -> Path:
    """Overlay `cloud` onto an existing project directory and record it in platform.toml."""
    meta = Manifest.of(project).project
    type_ = meta.get("type", "")
    language = meta.get("language", "")

    if not cloud.supports(type_, language):
        raise TemplateError(
            f"cloud {cloud.name} does not support {type_}/{language} "
            f"(types: {cloud.types or 'any'}, languages: {cloud.languages or 'any'})"
        )

    root = cloud.root or repo

    if (root / cloud.directory / "cookiecutter.json").exists():
        _render_over(
            root,
            cloud.directory,
            project,
            {
                "project_name": meta.get("name", project.name),
                "github_owner": meta.get("github_owner", "actionplatform"),
                "language": language,
                "type": type_,
                "ci": meta.get("ci", "github"),
            },
        )
    else:
        _copy_overlay(root / cloud.directory, project)

    Manifest.of(project).set_deploy_target(cloud.name)

    return project


def _render_over(repo: Path, directory: str, project: Path, extra: dict) -> None:
    """Render a cookiecutter overlay with the project's own name as `project_slug` — not the directory it happens to live in, which on the platform is a registry id — and lay the files over the project."""
    slug = extra["project_name"]

    with tempfile.TemporaryDirectory(prefix="ap-overlay-") as tmp:
        rendered = _cookiecutter(
            repo, directory, Path(tmp), {**extra, "project_slug": slug}
        )
        _copy_overlay(rendered, project)


def _copy_overlay(source: Path, project: Path) -> None:
    """A plain overlay — no cookiecutter.json — is copied as it is, file over file."""
    for item in source.rglob("*"):
        if not item.is_file():
            continue

        target = project / item.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def apply_service(
    repo: Path, service: Service, project: Path, provider: str | None = None
) -> Path:
    """Add `services/<name>/` to the project and record it under [services] in platform.toml."""
    meta = Manifest.of(project).project
    provider = provider or (service.providers[0] if service.providers else "")

    if service.providers and provider not in service.providers:
        raise TemplateError(
            f"service {service.name} has no provider {provider!r} "
            f"(available: {', '.join(service.providers)})"
        )

    existing = project / "services" / service.name
    if existing.exists():
        shutil.rmtree(existing)

    _render_over(
        repo,
        service.directory,
        project,
        {
            "project_name": meta.get("name", project.name),
            "github_owner": meta.get("github_owner", "actionplatform"),
            "provider": provider,
        },
    )

    Manifest.of(project).set_service(service.name, provider)

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

    if credentials is not None and credentials.token and config.source_host is not None:
        config.source_host = build_source_host(
            credentials.kind,
            config.source_host.repo,
            base_url=credentials.base_url,
            token=credentials.token,
            username=credentials.username,
        )

    if config.source_host is None:
        raise TemplateError("platform.toml has no [source_host]; cannot push")

    meta = Manifest.of(project).project
    repo = (
        Repository(project)
        if (project / ".git").exists()
        else Repository.init(project, branch=branch)
    )

    wired.gitflow(repo).install_hooks()
    repo.add_all()

    if not repo.is_clean():
        repo.commit("chore: bootstrap project from action-platform")

    url = config.source_host.create_repository(
        config.source_host.repo,
        description=meta.get("description", ""),
        private=private,
    )

    if not repo.remote_url():
        repo.add_remote(url)

    try:
        repo.push_upstream(branch)
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


@slot("scaffolder")
class Scaffolder:
    """Generating a project, overlaying a cloud, adding a service, pushing the result — the module's functions as one replaceable class."""

    def generate(
        self,
        repo: Path,
        leaf: Leaf,
        name: str,
        ci: str | None,
        output: Path,
        extra: dict | None = None,
    ) -> Path:
        return generate_project(repo, leaf, name, ci, output, extra)

    def apply_cloud(self, repo: Path, cloud: Cloud, project: Path) -> Path:
        return apply_cloud(repo, cloud, project)

    def apply_service(
        self, repo: Path, service: Service, project: Path, provider: str | None = None
    ) -> Path:
        return apply_service(repo, service, project, provider)

    def push(
        self,
        project: Path,
        private: bool = False,
        branch: str = "main",
        credentials: "SourceCredentialsLike | None" = None,
    ) -> str:
        return push_project(project, private, branch, credentials)
