"""Generate projects from leaves, overlay clouds and services on them, push the result: the steps in order, rendering, platform.toml and git each done by its own class."""

from __future__ import annotations

import shutil
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.workflow import slugify
from action_platform.core.manifest import Manifest
from action_platform.core.scaffold.publisher import SourceCredentialsLike, push_project
from action_platform.core.scaffold.renderer import TemplateRenderer
from action_platform.core.scaffold.templates import Cloud, Leaf, Service
from action_platform.core.wiring import slot, wired
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

    return TemplateRenderer().render(repo, leaf.directory, output, context)


def _copy_repository(
    repo: Path, leaf: Leaf, name: str, ci: str | None, output: Path, context: dict
) -> Path:
    """Copy a plain repository as the new project and make sure it carries platform.toml, hooks and CI."""
    slug = slugify(name)
    target = output / slug

    if target.exists():
        raise TemplateError(f"{target} already exists")

    shutil.copytree(repo, target, ignore=shutil.ignore_patterns(".git"))
    manifest = Manifest.of(target)

    if not (target / settings.LAST_VERSION_FILE).exists():
        (target / settings.LAST_VERSION_FILE).write_text("0.0.0\n")

    if manifest.exists:
        manifest.rename(slug)
        _set_owner(manifest, context.get("github_owner"))
        return target

    Repository.init(target, branch="main")

    if leaf.stack:
        wired.installer(target, type_=leaf.type, language=leaf.stack, ci=ci).apply()
    else:
        manifest.path.write_text(
            f'[project]\nname = "{slug}"\ntype = "{leaf.type}"\nci = "{ci or "github"}"\n'
            '\n[release]\nstrategy = "semver"\nchangelog = "conventional"\n'
        )
        (target / settings.LAST_VERSION_FILE).write_text("0.0.0\n")

    shutil.rmtree(target / ".git", ignore_errors=True)
    _set_owner(manifest, context.get("github_owner"))

    if context.get("description"):
        manifest.set_description(str(context["description"]))

    return target


def _set_owner(manifest: Manifest, owner: str | None) -> None:
    if owner and manifest.exists:
        manifest.set_owner(owner)


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
    renderer = TemplateRenderer()

    if (root / cloud.directory / "cookiecutter.json").exists():
        renderer.overlay(
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
        renderer.copy(root / cloud.directory, project)

    Manifest.of(project).set_deploy_target(cloud.name)

    return project


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

    TemplateRenderer().overlay(
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
        credentials: SourceCredentialsLike | None = None,
    ) -> str:
        return push_project(project, private, branch, credentials)
