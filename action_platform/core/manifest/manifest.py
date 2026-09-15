"""platform.toml: the file that declares a project. Read and edit its tables without touching the rest."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from action_platform.core.exception import TemplateError
from action_platform.settings import settings

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}

OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
REPO_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
)


def toml_str(value: str) -> str:
    """`value` as a TOML basic string, quotes included: anything the user typed stays inside the quotes."""
    out = []

    for ch in value:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20 or ch == "\x7f":
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)

    return '"' + "".join(out) + '"'


def check_owner(owner: str) -> str:
    if not OWNER_RE.match(owner):
        raise TemplateError(f"invalid repository owner: {owner!r}")

    return owner


def check_repo(repo: str) -> str:
    if not REPO_RE.match(repo):
        raise TemplateError(f"invalid repository name: {repo!r} (expected owner/name)")

    return repo


class Manifest:
    """platform.toml as an object: parsed once, edited table by table, the rest of the file left as written."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @classmethod
    def of(cls, project: Path) -> "Manifest":
        return cls(Path(project) / settings.CONFIG_FILE)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def text(self) -> str:
        return self.path.read_text()

    def data(self) -> dict:
        if not self.path.exists():
            raise TemplateError(
                f"{settings.CONFIG_FILE} not found in {self.path.parent}"
            )

        return tomllib.loads(self.path.read_text())

    @property
    def project(self) -> dict:
        data = self.data()
        meta = dict(data.get("project", {}))
        repo = data.get("source_host", {}).get("repo", "")

        if "/" in repo:
            meta["github_owner"] = repo.split("/", 1)[0]

        return meta

    @property
    def source_host(self) -> dict:
        return dict(self.data().get("source_host", {}))

    @property
    def services(self) -> dict:
        return dict(self.data().get("services", {}))

    def set_source_host(
        self, kind: str, repo: str, base_url: str | None = None
    ) -> None:
        """Replace (or add) the [source_host] table."""
        text = self.text()
        block = f"[source_host]\nkind = {toml_str(kind)}\nrepo = {toml_str(check_repo(repo))}\n"

        if base_url:
            block += f"base_url = {toml_str(base_url)}\n"

        if "[source_host]" in text:
            text = re.sub(r"\[source_host\]\n(?:[^\[\n][^\n]*\n?)*", block, text)
        else:
            text = text.rstrip("\n") + "\n\n" + block

        self.path.write_text(text)

    def set_deploy_target(self, target: str) -> None:
        text = self.text()
        line = f"target = {toml_str(target)}"

        if "[deploy]" not in text:
            self.path.write_text(text.rstrip("\n") + f"\n\n[deploy]\n{line}\n")
            return

        lines = text.splitlines()

        for i, current in enumerate(lines):
            if current.strip().startswith("target ="):
                lines[i] = line
                break
        else:
            lines.insert(lines.index("[deploy]") + 1, line)

        self.path.write_text("\n".join(lines) + "\n")

    def set_service(self, name: str, provider: str) -> None:
        text = self.text()
        line = f"{name} = {toml_str(provider)}"

        if "[services]" not in text:
            self.path.write_text(text.rstrip("\n") + f"\n\n[services]\n{line}\n")
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

        self.path.write_text("\n".join(lines) + "\n")


def write_source_host(
    path: Path, kind: str, repo: str, base_url: str | None = None
) -> None:
    Manifest(path).set_source_host(kind, repo, base_url)


def read_platform(project: Path) -> dict:
    return Manifest.of(project).project


def write_deploy_target(path: Path, target: str) -> None:
    Manifest(path).set_deploy_target(target)


def write_service(path: Path, name: str, provider: str) -> None:
    Manifest(path).set_service(name, provider)
