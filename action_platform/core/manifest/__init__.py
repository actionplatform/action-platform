"""platform.toml: the file that declares a project. Read and edit its tables without touching the rest."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.settings import settings


def write_source_host(
    path: Path, kind: str, repo: str, base_url: str | None = None
) -> None:
    """Replace (or add) the [source_host] table in platform.toml."""
    text = path.read_text()
    block = f'[source_host]\nkind = "{kind}"\nrepo = "{repo}"\n'

    if base_url:
        block += f'base_url = "{base_url}"\n'

    if "[source_host]" in text:
        text = re.sub(r"\[source_host\]\n(?:[^\[\n][^\n]*\n?)*", block, text)
    else:
        text = text.rstrip("\n") + "\n\n" + block

    path.write_text(text)


def read_platform(project: Path) -> dict:
    path = project / settings.CONFIG_FILE

    if not path.exists():
        raise TemplateError(f"{settings.CONFIG_FILE} not found in {project}")

    data = tomllib.loads(path.read_text())
    meta = dict(data.get("project", {}))
    repo = data.get("source_host", {}).get("repo", "")

    if "/" in repo:
        meta["github_owner"] = repo.split("/", 1)[0]

    return meta


def write_deploy_target(path: Path, target: str) -> None:
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


def write_service(path: Path, name: str, provider: str) -> None:
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
