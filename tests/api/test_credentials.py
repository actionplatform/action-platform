"""git_auth injects a credential helper through the environment and restores it."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from action_platform.api.credentials import SourceCredentials, git_auth  # noqa: E402


def test_git_auth_sets_and_restores_env(monkeypatch):
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    creds = SourceCredentials(kind="gitlab", token="glpat-x")

    with git_auth(creds):
        assert os.environ["GIT_CONFIG_KEY_0"] == "credential.helper"
        assert os.environ["AP_GIT_USER"] == "oauth2"
        assert os.environ["AP_GIT_TOKEN"] == "glpat-x"
        assert os.environ["GIT_TERMINAL_PROMPT"] == "0"

    assert "GIT_CONFIG_COUNT" not in os.environ
    assert "AP_GIT_TOKEN" not in os.environ


def test_git_reads_helper_from_env(tmp_path: Path):
    """git credential fill must answer with the injected user/token."""
    creds = SourceCredentials(kind="github", token="ghp_test")

    with git_auth(creds):
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=True,
        ).stdout

    assert "username=x-access-token" in out
    assert "password=ghp_test" in out


def test_git_auth_none_is_noop():
    before = dict(os.environ)
    with git_auth(None):
        pass
    assert dict(os.environ) == before
