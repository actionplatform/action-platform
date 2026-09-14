"""Shared base classes and builders for the unittest suites."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

GIT_IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@t"]


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


class TempCase(unittest.TestCase):
    """A fresh temporary directory in `self.tmp_path` and an isolated copy of the environment per test."""

    def setUp(self) -> None:
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name).resolve()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        self.setenv("GIT_AUTHOR_NAME", "t")
        self.setenv("GIT_AUTHOR_EMAIL", "t@t")
        self.setenv("GIT_COMMITTER_NAME", "t")
        self.setenv("GIT_COMMITTER_EMAIL", "t@t")

    def setenv(self, name: str, value: str) -> None:
        os.environ[name] = value

    def delenv(self, name: str) -> None:
        os.environ.pop(name, None)

    def patch(
        self, target: Any, attribute: str | None = None, value: Any = None
    ) -> Any:
        """`patch(obj, "attr", value)` or `patch("dotted.path", value=...)`; undone after the test."""
        if isinstance(target, str) and attribute is None:
            patcher = mock.patch(target, value)
        elif isinstance(target, str):
            patcher = mock.patch(f"{target}.{attribute}", value)
        else:
            patcher = mock.patch.object(target, attribute, value)

        started = patcher.start()
        self.addCleanup(patcher.stop)

        return started


def repo_with_origin(
    root: Path, files: dict[str, str] | None = None, message: str = "chore: init"
) -> Path:
    """A working clone at root/work with a bare origin at root/origin.git and one commit on main."""
    origin = root / "origin.git"
    git(root, "init", "-q", "--bare", "-b", "main", str(origin))
    work = root / "work"
    git(root, "clone", "-q", str(origin), str(work))

    for rel, text in (files or {"README.md": "x\n"}).items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    git(work, "add", "-A")
    git(work, "commit", "-qm", message)
    git(work, "push", "-q", "-u", "origin", "main")

    return work


PLATFORM = """
[project]
name = "demo"
type = "web"
language = "python"

[source_host]
kind = "github"
repo = "acme/demo"
"""


def platform_repo(root: Path) -> Path:
    """The API fixture: a platform project on main, tagged v1.2.3, with a feature/1 branch on top."""
    repo = root / "demo"
    repo.mkdir()
    (repo / "platform.toml").write_text(PLATFORM)
    (repo / "LAST_VERSION").write_text("1.2.3\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: bootstrap project")
    git(repo, "tag", "v1.2.3")
    git(repo, "checkout", "-q", "-b", "feature/1")
    (repo / "a.txt").write_text("a")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "feat: add a")

    return repo


def git_repo(
    root: Path,
    files: dict[str, str],
    message: str = "chore: init",
    branch: str = "main",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    git(root, "init", "-q", "-b", branch)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)

    return root


INDEX = json.dumps(
    {
        "projects": [
            {"id": "web/python/fastapi", "default": True, "description": "FastAPI"}
        ],
        "clouds": [
            {
                "id": "docker",
                "description": "Dockerfile",
                "languages": ["python"],
                "types": ["web"],
            }
        ],
        "services": [{"id": "postgres", "description": "db", "providers": ["docker"]}],
    }
)

COOKIECUTTER = {
    "project_name": "My Project",
    "project_slug": "{{ cookiecutter.project_name|lower|replace(' ', '-') }}",
    "description": "tiny",
    "package_name": "{{ cookiecutter.project_slug|replace('-', '_') }}",
    "github_owner": "acme",
    "ci": ["github", "gitlab", "jenkins"],
}


def template_repo(
    root: Path,
    type_: str = "web",
    stack: str = "python",
    template: str = "fastapi",
    rendered: bool = False,
) -> Path:
    """A minimal templates repository with one leaf. `rendered=True` adds a README and package so cookiecutter output can be inspected."""
    leaf = root / "projects" / type_ / stack / template
    slug = leaf / "{{cookiecutter.project_slug}}"
    slug.mkdir(parents=True)
    (leaf / "cookiecutter.json").write_text(
        json.dumps({**COOKIECUTTER, "_language": stack})
    )
    (slug / "platform.toml").write_text(
        '[project]\nname = "{{ cookiecutter.project_slug }}"\n'
        f'type = "{type_}"\nlanguage = "{stack}"\n'
        'ci = "{{ cookiecutter.ci }}"\n\n'
        '[source_host]\nkind = "github"\nrepo = "{{ cookiecutter.github_owner }}/{{ cookiecutter.project_slug }}"\n'
    )
    (root / "index.json").write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "id": f"{type_}/{stack}/{template}",
                        "default": True,
                        "description": template,
                    }
                ]
            }
        )
    )

    (slug / ".code_quality").mkdir()
    (slug / ".code_quality" / "ruff.toml").write_text("line-length = 79\n")
    (slug / ".github" / "workflows").mkdir(parents=True)

    for w in ["code-quality.yml", "gitflow.yml"]:
        (slug / ".github" / "workflows" / w).write_text("name: x\n")

    (slug / ".gitlab-ci.yml").write_text("image: x\n")
    (slug / "Jenkinsfile").write_text("pipeline {}\n")
    (slug / "bitbucket-pipelines.yml").write_text("image: x\n")

    if rendered:
        (slug / "README.md").write_text(
            "# {{ cookiecutter.project_name }}\n{{ cookiecutter.description }}\n"
        )
        (slug / "{{cookiecutter.package_name}}").mkdir()
        (slug / "{{cookiecutter.package_name}}" / "__init__.py").write_text("")

    return root


def install_templates(root: Path) -> Path:
    """Templates with the files `action-platform install` borrows: .code_quality and CI files."""
    leaf = root / "projects/web/python/fastapi"
    proj = leaf / "{{cookiecutter.project_slug}}"
    leaf.mkdir(parents=True)
    (leaf / "cookiecutter.json").write_text('{"_language": "python"}')
    (proj / ".code_quality").mkdir(parents=True)
    (proj / ".code_quality/ruff.toml").write_text("line-length = 79\n")
    (proj / ".github/workflows").mkdir(parents=True)

    for w in ["code-quality.yml", "gitflow.yml"]:
        (proj / ".github/workflows" / w).write_text("name: x\n")

    (proj / ".gitlab-ci.yml").write_text("image: x\n")
    (root / "index.json").write_text(
        json.dumps(
            {
                "projects": [
                    {"id": "web/python/fastapi", "default": True, "description": "x"}
                ]
            }
        )
    )

    return root
