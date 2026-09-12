"""Git plumbing wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def current_branch(cwd: Path | None = None) -> str:
    return run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)


def remote_url(cwd: Path | None = None, remote: str = "origin") -> str:
    try:
        return run(["remote", "get-url", remote], cwd=cwd)
    except subprocess.CalledProcessError:
        return ""


def is_clean(cwd: Path | None = None) -> bool:
    return run(["status", "--porcelain"], cwd=cwd) == ""


def latest_tag(cwd: Path | None = None) -> str | None:
    try:
        return run(["describe", "--tags", "--abbrev=0"], cwd=cwd)
    except subprocess.CalledProcessError:
        return None


def commits_since(tag: str | None, cwd: Path | None = None) -> list[str]:
    rng = f"{tag}..HEAD" if tag else "HEAD"
    out = run(["log", rng, "--pretty=format:%s"], cwd=cwd)

    return [line for line in out.split("\n") if line]


def create_tag(tag: str, message: str, cwd: Path | None = None) -> None:
    run(["tag", "-a", tag, "-m", message], cwd=cwd)


def push(
    refspec: str = "HEAD", remote: str = "origin", cwd: Path | None = None
) -> None:
    run(["push", remote, refspec], cwd=cwd)


def push_tag(tag: str, remote: str = "origin", cwd: Path | None = None) -> None:
    run(["push", remote, tag], cwd=cwd)


def checkout_branch(branch: str, create: bool = False, cwd: Path | None = None) -> None:
    args = ["checkout"]

    if create:
        args.append("-b")

    args.append(branch)
    run(args, cwd=cwd)


def commit(message: str, cwd: Path | None = None) -> None:
    run(["commit", "-am", message], cwd=cwd)


def init(cwd: Path, branch: str = "main") -> None:
    run(["init", "-q", "-b", branch], cwd=cwd)


def add_all(cwd: Path) -> None:
    run(["add", "-A"], cwd=cwd)


def add_remote(url: str, cwd: Path, remote: str = "origin") -> None:
    run(["remote", "add", remote, url], cwd=cwd)


def push_upstream(branch: str, cwd: Path, remote: str = "origin") -> None:
    run(["push", "-u", remote, branch], cwd=cwd)
