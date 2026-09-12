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
    try:
        return run(["symbolic-ref", "--short", "-q", "HEAD"], cwd=cwd)
    except subprocess.CalledProcessError:
        return run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)


def remote_url(cwd: Path | None = None, remote: str = "origin") -> str:
    try:
        return run(["remote", "get-url", remote], cwd=cwd)
    except subprocess.CalledProcessError:
        return ""


def is_clean(cwd: Path | None = None) -> bool:
    return run(["status", "--porcelain"], cwd=cwd) == ""


def latest_tag(cwd: Path | None = None, match: str | None = None) -> str | None:
    """Closest reachable tag; `match` is a glob such as "web/v*"."""
    args = ["describe", "--tags", "--abbrev=0"]

    if match:
        args += ["--match", match]

    try:
        return run(args, cwd=cwd)
    except subprocess.CalledProcessError:
        return None


def commits_since(
    tag: str | None, cwd: Path | None = None, paths: list[str] | None = None
) -> list[str]:
    """Subjects since `tag`; `paths` are git pathspecs (":!dir" excludes)."""
    rng = f"{tag}..HEAD" if tag else "HEAD"
    args = ["log", rng, "--pretty=format:%s"]

    if paths:
        args += ["--", *paths]

    out = run(args, cwd=cwd)

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


def add(paths: list[str], cwd: Path | None = None) -> None:
    run(["add", "--", *paths], cwd=cwd)


def commit(message: str, cwd: Path | None = None) -> None:
    run(["commit", "-m", message], cwd=cwd)


def init(cwd: Path, branch: str = "main") -> None:
    run(["init", "-q", "-b", branch], cwd=cwd)


def add_all(cwd: Path) -> None:
    run(["add", "-A"], cwd=cwd)


def add_remote(url: str, cwd: Path, remote: str = "origin") -> None:
    run(["remote", "add", remote, url], cwd=cwd)


def push_upstream(branch: str, cwd: Path, remote: str = "origin") -> None:
    run(["push", "-u", remote, branch], cwd=cwd)


def tags(cwd: Path | None = None) -> list[str]:
    out = run(["tag", "--list"], cwd=cwd)

    return [t for t in out.split("\n") if t]


def remote_tag_exists(
    tag: str, cwd: Path | None = None, remote: str = "origin"
) -> bool:
    try:
        out = run(["ls-remote", "--tags", remote, tag], cwd=cwd)
    except subprocess.CalledProcessError:
        return False

    return bool(out.strip())
