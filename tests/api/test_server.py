"""Registry and the read-only endpoints over a throwaway git repo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from action_platform.api.registry import Registry  # noqa: E402
from action_platform.api.server import build  # noqa: E402

PLATFORM = """
[project]
name = "demo"
type = "web"
language = "python"

[source_host]
kind = "github"
repo = "acme/demo"
"""


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    root.mkdir()
    (root / "platform.toml").write_text(PLATFORM)
    (root / "LAST_VERSION").write_text("1.2.3\n")
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@t", cwd=root)
    git("config", "user.name", "t", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "chore: bootstrap project", cwd=root)
    git("tag", "v1.2.3", cwd=root)
    git("checkout", "-q", "-b", "feature/1", cwd=root)
    (root / "a.txt").write_text("a")
    git("add", "a.txt", cwd=root)
    git("commit", "-q", "-m", "feat: add a", cwd=root)

    return root


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AP_HOME", str(tmp_path / "home"))

    return TestClient(build())


def test_registry_roundtrip(tmp_path: Path, repo: Path):
    reg = Registry(tmp_path / "projects.json")

    entry = reg.add(repo)
    assert reg.add(repo).id == entry.id
    assert [e.name for e in reg.list()] == ["demo"]

    reg.remove(entry.id)
    assert reg.list() == []


def test_registry_refuses_dir_without_platform(tmp_path: Path):
    with pytest.raises(Exception, match="platform.toml"):
        Registry(tmp_path / "projects.json").add(tmp_path)


def test_projects_crud(client: TestClient, repo: Path):
    assert client.get("/api/projects").json() == []

    created = client.post("/api/projects", json={"path": str(repo)})
    assert created.status_code == 201
    id = created.json()["id"]

    rows = client.get("/api/projects").json()
    assert rows[0]["name"] == "demo"
    assert rows[0]["branch"] == "feature/1"
    assert rows[0]["last_version"] == "1.2.3"

    assert client.delete(f"/api/projects/{id}").status_code == 204
    assert client.get(f"/api/projects/{id}").status_code == 400


def test_project_detail_and_git(client: TestClient, repo: Path):
    id = client.post("/api/projects", json={"path": str(repo)}).json()["id"]

    detail = client.get(f"/api/projects/{id}").json()
    assert detail["project"]["name"] == "demo"
    assert detail["source_host"]["repo"] == "acme/demo"
    assert detail["latest_tag"] == "v1.2.3"
    assert detail["clean"] is True

    audit = client.get(f"/api/projects/{id}/gitflow").json()
    assert audit["ok"] is True
    assert audit["checked_commits"] == 1

    commits = client.get(f"/api/projects/{id}/commits?limit=5").json()
    assert commits[0]["subject"] == "feat: add a"

    branches = {b["name"]: b for b in client.get(f"/api/projects/{id}/branches").json()}
    assert branches["main"]["protected"] is True
    assert branches["feature/1"]["kind"] == "feature"

    assert client.get(f"/api/projects/{id}/tags").json() == ["v1.2.3"]


def test_unknown_project_is_400(client: TestClient):
    assert client.get("/api/projects/nope").status_code == 400


def test_static_endpoints(client: TestClient):
    assert "version" in client.get("/api/version").json()
    rules = client.get("/api/gitflow/rules").json()
    assert "feature" in rules["kinds"]
    assert "main" in rules["protected"]
