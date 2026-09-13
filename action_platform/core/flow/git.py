"""Git plumbing wrappers."""

from __future__ import annotations

import os
import re
import subprocess
from contextvars import ContextVar
from pathlib import Path


AUTH_ENV: ContextVar[dict[str, str] | None] = ContextVar("git_auth_env", default=None)


class UnsafeUrl(ValueError):
    pass


class BadRef(ValueError):
    pass


REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def check_ref(name: str) -> str:
    """A branch or tag name that is safe to hand to git as an argument: no leading dash, no path tricks."""
    if (
        not name
        or not REF_RE.match(name)
        or ".." in name
        or "@{" in name
        or name.endswith(".lock")
        or name.endswith("/")
        or "//" in name
    ):
        raise BadRef(f"invalid git ref: {name!r}")

    return name


def check_remote_url(url: str) -> str:
    """Only https (and http / file when the operator opted in) may be cloned or fetched on behalf of a user; ACTION_PLATFORM_GIT_HOSTS narrows the hosts further."""
    from urllib.parse import urlsplit

    from action_platform.settings import settings

    parts = urlsplit(url)
    allowed = (
        parts.scheme == "https"
        or (parts.scheme == "http" and settings.ALLOW_INSECURE_HTTP)
        or (parts.scheme == "file" and settings.ALLOW_FILE_URLS)
    )

    if not allowed:
        raise UnsafeUrl(f"unsupported git url: {url} (https:// only)")

    host = (parts.hostname or "").lower()

    if (
        parts.scheme != "file"
        and settings.GIT_HOSTS
        and not any(host == h or host.endswith("." + h) for h in settings.GIT_HOSTS)
    ):
        raise UnsafeUrl(
            f"git host {host} is not allowed (ACTION_PLATFORM_GIT_HOSTS: {', '.join(settings.GIT_HOSTS)})"
        )

    return url


def git_env() -> dict[str, str]:
    """Environment for a git subprocess: the process environment, the credentials of the current request, and a protocol policy: https always, http only when opted in, ssh/git never, local paths only for direct commands (never from submodules)."""
    from action_platform.settings import settings

    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    extra = {**(AUTH_ENV.get() or {})}
    count = int(extra.get("GIT_CONFIG_COUNT", "0"))
    policy = {
        "protocol.allow": "never",
        "protocol.https.allow": "always",
        "protocol.http.allow": "always" if settings.ALLOW_INSECURE_HTTP else "never",
        "protocol.file.allow": "always" if settings.ALLOW_FILE_URLS else "user",
    }

    for key, value in policy.items():
        extra[f"GIT_CONFIG_KEY_{count}"] = key
        extra[f"GIT_CONFIG_VALUE_{count}"] = value
        count += 1

    extra["GIT_CONFIG_COUNT"] = str(count)
    env.update(extra)

    return env


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=git_env(),
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
    name = check_ref(branch)
    args = (
        ["checkout", "-b", name] if create else ["checkout", "--end-of-options", name]
    )
    run(args, cwd=cwd)


def add(paths: list[str], cwd: Path | None = None) -> None:
    run(["add", "--", *paths], cwd=cwd)


def commit(message: str, cwd: Path | None = None) -> None:
    run(["commit", "-m", message, "--end-of-options"], cwd=cwd)


def init(cwd: Path, branch: str = "main") -> None:
    run(["init", "-q", "-b", branch], cwd=cwd)


def add_all(cwd: Path) -> None:
    run(["add", "-A"], cwd=cwd)


def add_remote(url: str, cwd: Path, remote: str = "origin") -> None:
    run(["remote", "add", remote, url], cwd=cwd)


def push_upstream(branch: str, cwd: Path, remote: str = "origin") -> None:
    run(["push", "-u", "--end-of-options", remote, check_ref(branch)], cwd=cwd)


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
