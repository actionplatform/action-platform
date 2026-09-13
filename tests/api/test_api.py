"""Registry and the read-only endpoints over a throwaway git repo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from action_platform.api.repositories.registry import Registry  # noqa: E402
from action_platform.settings import settings  # noqa: E402
from action_platform.api.main import build  # noqa: E402

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
def url(repo: Path) -> str:
    return repo.as_uri()


@pytest.fixture(autouse=True)
def _file_urls(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_FILE_URLS", True)


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AP_HOME", str(tmp_path / "home"))

    return TestClient(build())


def test_registry_clones_into_workspace(tmp_path: Path, url: str):
    reg = Registry(tmp_path / "home")

    entry = reg.add(url)
    assert entry.name == "demo"
    assert entry.default_branch == "feature/1"
    assert Path(entry.path).is_relative_to(tmp_path / "home" / "workspaces")
    assert (Path(entry.path) / "platform.toml").exists()
    assert reg.add(url).id == entry.id

    reg.remove(entry.id)
    assert reg.list() == []
    assert not Path(entry.path).exists()


def test_registry_refuses_repo_without_platform(tmp_path: Path):
    bare = tmp_path / "plain"
    bare.mkdir()
    git("init", "-q", cwd=bare)
    git("config", "user.email", "t@t", cwd=bare)
    git("config", "user.name", "t", cwd=bare)
    (bare / "x").write_text("x")
    git("add", "x", cwd=bare)
    git("commit", "-q", "-m", "chore: x", cwd=bare)

    reg = Registry(tmp_path / "home")
    with pytest.raises(Exception, match="platform.toml"):
        reg.add(bare.as_uri())
    assert not any((tmp_path / "home" / "workspaces").glob("*"))


def test_registry_refuses_non_url(tmp_path: Path):
    with pytest.raises(Exception, match="https:// only"):
        Registry(tmp_path / "home").add("/some/local/path")


def test_apps_crud(client: TestClient, url: str):
    assert client.get("/api/apps").json() == []

    created = client.post("/api/apps", json={"url": url})
    assert created.status_code == 201
    id = created.json()["id"]

    rows = client.get("/api/apps").json()
    assert rows[0]["name"] == "demo"
    assert rows[0]["url"] == url
    assert rows[0]["branch"] == "feature/1"
    assert rows[0]["last_version"] == "1.2.3"

    assert client.post(f"/api/apps/{id}/sync").status_code == 200

    assert client.delete(f"/api/apps/{id}").status_code == 204
    assert client.get(f"/api/apps/{id}").status_code == 400


def test_project_detail_and_git(client: TestClient, url: str):
    id = client.post("/api/apps", json={"url": url}).json()["id"]

    detail = client.get(f"/api/apps/{id}").json()
    assert detail["project"]["name"] == "demo"
    assert detail["url"] == url
    assert detail["source_host"]["repo"] == "acme/demo"
    assert detail["latest_tag"] == "v1.2.3"
    assert detail["clean"] is True

    audit = client.get(f"/api/apps/{id}/gitflow").json()
    assert audit["ok"] is True
    assert audit["checked_commits"] == 1

    commits = client.get(f"/api/apps/{id}/commits?limit=5").json()
    assert commits[0]["subject"] == "feat: add a"

    branches = {b["name"]: b for b in client.get(f"/api/apps/{id}/branches").json()}
    assert branches["main"]["protected"] is True
    assert branches["feature/1"]["kind"] == "feature"

    assert client.get(f"/api/apps/{id}/tags").json() == ["v1.2.3"]


def test_unknown_project_is_400(client: TestClient):
    assert client.get("/api/apps/nope").status_code == 400


def test_static_endpoints(client: TestClient):
    assert "version" in client.get("/api/version").json()
    rules = client.get("/api/gitflow/rules").json()
    assert "feature" in rules["kinds"]
    assert "main" in rules["protected"]


TEMPLATE_INDEX = """
[projects.web.python.mini]
default = true
description = "tiny"
"""

COOKIECUTTER = {
    "project_name": "My Project",
    "project_slug": "{{ cookiecutter.project_name|lower|replace(' ', '-') }}",
    "description": "tiny",
    "package_name": "{{ cookiecutter.project_slug|replace('-', '_') }}",
    "github_owner": "acme",
    "ci": ["github", "gitlab", "jenkins"],
}


@pytest.fixture
def templates(tmp_path: Path, monkeypatch) -> Path:
    import json

    root = tmp_path / "templates"
    leaf = root / "projects" / "web" / "python" / "mini"
    slug = leaf / "{{cookiecutter.project_slug}}"
    slug.mkdir(parents=True)
    (root / "index.toml").write_text(TEMPLATE_INDEX)
    (leaf / "cookiecutter.json").write_text(json.dumps(COOKIECUTTER))
    (slug / "platform.toml").write_text(
        '[project]\nname = "{{ cookiecutter.project_slug }}"\ntype = "web"\nlanguage = "python"\nci = "{{ cookiecutter.ci }}"\n\n'
        '[source_host]\nkind = "github"\nrepo = "{{ cookiecutter.github_owner }}/{{ cookiecutter.project_slug }}"\n'
    )
    (slug / "README.md").write_text(
        "# {{ cookiecutter.project_name }}\n{{ cookiecutter.description }}\n"
    )
    (slug / "{{cookiecutter.package_name}}").mkdir()
    (slug / "{{cookiecutter.package_name}}" / "__init__.py").write_text("")
    monkeypatch.setattr("action_platform.settings.settings.TEMPLATES_DIR", str(root))

    return root


def test_init_generates_workspace(client: TestClient, templates: Path, tmp_path: Path):
    res = client.post(
        "/api/apps/init",
        json={
            "type": "web",
            "stack": "python",
            "template": "mini",
            "name": "Orders Api",
            "description": "orders",
            "package_name": "orders",
            "ci": "gitlab",
            "git_init": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "orders-api"
    assert body["pushed"] is False
    assert body["url"] == ""

    path = Path(body["path"])
    assert path.is_relative_to(tmp_path / "home" / "action-platform" / "workspaces")
    assert (path / "orders" / "__init__.py").exists()
    assert "orders" in (path / "README.md").read_text()
    assert 'ci = "gitlab"' in (path / "platform.toml").read_text()
    assert (path / ".git").is_dir()
    assert not any(p.name.startswith(".init-") for p in path.parent.iterdir())

    detail = client.get(f"/api/apps/{body['id']}").json()
    assert detail["branch"] == "main"
    assert detail["clean"] is True
    assert detail["url"] == ""

    rows = client.get("/api/apps").json()
    assert rows[0]["name"] == "orders-api"


def test_init_without_git(client: TestClient, templates: Path):
    body = client.post(
        "/api/apps/init",
        json={"type": "web", "stack": "python", "name": "plain", "git_init": False},
    ).json()
    assert not (Path(body["path"]) / ".git").exists()
    detail = client.get(f"/api/apps/{body['id']}").json()
    assert detail["branch"] == ""


def test_init_unknown_type_is_400(client: TestClient, templates: Path):
    res = client.post("/api/apps/init", json={"type": "nope", "name": "x"})
    assert res.status_code == 400
    assert "unknown type" in res.json()["detail"]


def test_releases_from_tags(client: TestClient, url: str):
    id = client.post("/api/apps", json={"url": url}).json()["id"]
    rows = client.get(f"/api/apps/{id}/releases").json()
    assert rows[0]["tag"] == "v1.2.3"
    assert rows[0]["version"] == "1.2.3"
    assert rows[0]["latest"] is True
    assert rows[0]["prerelease"] is False
    assert len(rows[0]["sha"]) == 7


def test_start_branch_and_checkout(client: TestClient, url: str, repo: Path):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]
    res = client.post(
        f"/api/apps/{id}/branches",
        json={"kind": "feature", "code": "7", "slug": "login", "push": False},
    )
    assert res.status_code == 201, res.text
    assert res.json() == {"branch": "feature/7-login", "base": "main", "pushed": False}
    assert client.get(f"/api/apps/{id}").json()["branch"] == "feature/7-login"

    assert (
        client.post(f"/api/apps/{id}/checkout", json={"branch": "main"}).json()[
            "branch"
        ]
        == "main"
    )
    bad = client.post(
        f"/api/apps/{id}/branches", json={"kind": "wip", "code": "1", "push": False}
    )
    assert bad.status_code == 400


def test_propose_pull_request(client: TestClient, url: str, repo: Path):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]
    client.post(f"/api/apps/{id}/checkout", json={"branch": "feature/1"})
    res = client.get(f"/api/apps/{id}/pull-request")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["head"] == "feature/1"
    assert body["base"] == "main"
    assert "feat: add a" in body["title"] or body["commits"] == ["feat: add a"]


def test_manifest_read_write_and_commit(client: TestClient, url: str, repo: Path):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]

    content = client.get(f"/api/apps/{id}/manifest").json()["content"]
    assert 'name = "demo"' in content

    bad = client.put(f"/api/apps/{id}/manifest", json={"content": "[project\nname = "})
    assert bad.status_code == 400

    res = client.put(
        f"/api/apps/{id}/manifest",
        json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
    )
    assert res.status_code == 200
    assert client.get(f"/api/apps/{id}").json()["deploy"] == {"target": "docker"}
    assert client.get(f"/api/apps/{id}").json()["clean"] is False

    refused = client.post(f"/api/apps/{id}/commit", json={"message": "update stuff"})
    assert refused.status_code == 400

    ok = client.post(
        f"/api/apps/{id}/commit",
        json={"message": "chore(platform): set docker deploy target"},
    )
    assert ok.status_code == 201, ok.text
    assert client.get(f"/api/apps/{id}").json()["clean"] is True
    assert (
        client.get(f"/api/apps/{id}/commits?limit=1")
        .json()[0]["subject"]
        .startswith("chore(platform)")
    )


def test_commit_on_new_branch(client: TestClient, url: str, repo: Path):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]
    content = client.get(f"/api/apps/{id}/manifest").json()["content"]
    client.put(
        f"/api/apps/{id}/manifest",
        json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
    )

    res = client.post(
        f"/api/apps/{id}/commit",
        json={
            "message": "chore: set docker deploy target",
            "branch": {"kind": "chore", "code": "42", "slug": "deploy target"},
            "push": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["branch"] == "chore/42-deploy-target"
    assert body["pushed"] is True
    assert body["pull_request"] is None

    state = client.get(f"/api/apps/{id}").json()
    assert state["branch"] == "chore/42-deploy-target"
    assert state["clean"] is True
    assert state["deploy"] == {"target": "docker"}
    names = {b["name"] for b in client.get(f"/api/apps/{id}/branches").json()}
    assert "chore/42-deploy-target" in names


def test_sync_without_upstream_is_a_noop(
    client: TestClient, tmp_path: Path, url: str, repo: Path
):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]
    path = next((tmp_path / "home" / "action-platform" / "workspaces").glob("*"))
    git("checkout", "-q", "-b", "chore/7-local-only", cwd=path)

    res = client.post(f"/api/apps/{id}/sync")
    assert res.status_code == 200, res.text
    assert client.get(f"/api/apps/{id}").json()["branch"] == "chore/7-local-only"


def test_release_dry_run_from_another_branch(client: TestClient, url: str, repo: Path):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]

    rc = client.post(
        f"/api/apps/{id}/release", json={"level": "minor", "branch": "feature/1"}
    )
    assert rc.status_code == 200, rc.text
    assert rc.json()["branch"] == "feature/1"
    assert rc.json()["prerelease"] is True
    assert rc.json()["next"].startswith("1.3.0-rc.")

    stable = client.post(
        f"/api/apps/{id}/release", json={"level": "minor", "branch": "main"}
    )
    assert stable.status_code == 200, stable.text
    assert stable.json()["branch"] == "main"
    assert stable.json()["prerelease"] is False
    assert stable.json()["next"] == "1.3.0"
    assert client.get(f"/api/apps/{id}").json()["branch"] == "main"


def test_matrix_merges_a_custom_source(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setenv(
        "ACTION_PLATFORM_TEMPLATES",
        str(_template_repo(tmp_path / "official", "web", "python", "fastapi")),
    )
    custom = _template_repo(tmp_path / "custom", "web", "go", "gin")
    git("init", "-q", "-b", "v1", cwd=custom)
    git("config", "user.email", "t@t", cwd=custom)
    git("config", "user.name", "t", cwd=custom)
    git("add", "-A", cwd=custom)
    git("commit", "-q", "-m", "chore: bootstrap templates", cwd=custom)

    res = client.post(
        "/api/matrix",
        json={
            "sources": [
                {"name": "acme", "url": custom.as_uri(), "ref": "v1"},
                {"name": "broken", "url": (tmp_path / "missing").as_uri()},
            ]
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    sources = {s["name"]: s for s in body["sources"]}
    assert sources["official"]["ok"] and sources["acme"]["ok"]
    assert sources["broken"]["ok"] is False and sources["broken"]["error"]
    by_source = {(p["source"], p["stack"]) for p in body["projects"]}
    assert ("official", "python") in by_source
    assert ("acme", "go") in by_source


def _template_repo(root: Path, type_: str, stack: str, template: str) -> Path:
    leaf = root / "projects" / type_ / stack / template
    (leaf / "{{cookiecutter.project_slug}}").mkdir(parents=True)
    (leaf / "cookiecutter.json").write_text(
        '{"project_name": "x", "project_slug": "x", "description": "", "package_name": "x", "github_owner": "o", "ci": "github"}'
    )
    (leaf / "{{cookiecutter.project_slug}}" / "platform.toml").write_text(
        f'[project]\nname = "x"\ntype = "{type_}"\nlanguage = "{stack}"\n'
    )
    (root / "index.toml").write_text(
        f'[projects.{type_}.{stack}.{template}]\ndefault = true\ndescription = "{template}"\n'
    )
    return root


def test_plain_repository_source_is_one_template(
    client: TestClient, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv(
        "ACTION_PLATFORM_TEMPLATES",
        str(_template_repo(tmp_path / "official", "web", "python", "fastapi")),
    )
    plain = tmp_path / "starter"
    (plain / "app").mkdir(parents=True)
    (plain / "app" / "main.py").write_text("print('hi')\n")
    (plain / "pyproject.toml").write_text('[project]\nname = "starter"\n')
    git("init", "-q", "-b", "main", cwd=plain)
    git("config", "user.email", "t@t", cwd=plain)
    git("config", "user.name", "t", cwd=plain)
    git("add", "-A", cwd=plain)
    git("commit", "-q", "-m", "chore: starter", cwd=plain)

    spec = {"name": "starter", "url": plain.as_uri(), "ref": "main"}
    matrix = client.post("/api/matrix", json={"sources": [spec]}).json()
    mine = [p for p in matrix["projects"] if p["source"] == "starter"]
    assert len(mine) == 1
    assert mine[0]["stack"] == "python" and mine[0]["template"] == "starter"

    res = client.post(
        "/api/apps/init",
        json={
            "type": mine[0]["type"],
            "stack": "python",
            "template": "starter",
            "name": "My Service",
            "source": spec,
            "push": False,
        },
    )
    assert res.status_code == 201, res.text
    created = res.json()
    detail = client.get(f"/api/apps/{created['id']}").json()
    assert created["name"] == "my-service"
    assert detail["project"]["language"] == "python"
    assert (Path(created["path"]) / "app" / "main.py").exists()
    assert (Path(created["path"]) / "platform.toml").exists()


def test_add_installs_platform_on_a_bare_repository(
    client: TestClient, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv(
        "ACTION_PLATFORM_TEMPLATES",
        str(_template_repo(tmp_path / "official", "web", "python", "fastapi")),
    )
    bare = tmp_path / "legacy"
    bare.mkdir()
    (bare / "pyproject.toml").write_text('[project]\nname = "legacy"\n')
    git("init", "-q", "-b", "main", cwd=bare)
    git("config", "user.email", "t@t", cwd=bare)
    git("config", "user.name", "t", cwd=bare)
    git("add", "-A", cwd=bare)
    git("commit", "-q", "-m", "chore: legacy", cwd=bare)

    refused = client.post("/api/apps", json={"url": bare.as_uri()})
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "needs_install"

    res = client.post(
        "/api/apps",
        json={"url": bare.as_uri(), "install": {"type": "web", "ci": "github"}},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "platform.toml" in body["installed"]
    detail = client.get(f"/api/apps/{body['id']}").json()
    assert detail["project"]["language"] == "python"
    assert detail["clean"] is False


def test_only_https_urls_are_cloned(tmp_path: Path, monkeypatch, url: str):
    monkeypatch.setenv("AP_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(settings, "ALLOW_FILE_URLS", False)
    client = TestClient(build())

    for bad in [
        url,
        "ssh://git@github.com/acme/repo.git",
        "git@github.com:acme/repo.git",
        "/tmp/repo",
    ]:
        res = client.post("/api/apps", json={"url": bad})
        assert res.status_code == 400, bad
        assert "https:// only" in res.json()["detail"]

    monkeypatch.setattr(settings, "GIT_HOSTS", ["github.com"])
    res = client.post("/api/apps", json={"url": "https://gitlab.com/acme/repo.git"})
    assert res.status_code == 400
    assert "not allowed" in res.json()["detail"]


def test_refs_that_look_like_options_are_refused(
    client: TestClient, url: str, repo: Path, tmp_path: Path, monkeypatch
):
    git("checkout", "-q", "main", cwd=repo)
    id = client.post("/api/apps", json={"url": url}).json()["id"]

    for bad in [
        "--upload-pack=touch /tmp/pwned",
        "-x",
        "a..b",
        "feature/@{1}",
        "x.lock",
        "dir/",
    ]:
        assert (
            client.post(f"/api/apps/{id}/checkout", json={"branch": bad}).status_code
            == 400
        ), bad
        assert (
            client.post(
                f"/api/apps/{id}/release", json={"level": "patch", "branch": bad}
            ).status_code
            == 400
        ), bad

    monkeypatch.setenv(
        "ACTION_PLATFORM_TEMPLATES",
        str(_template_repo(tmp_path / "official", "web", "python", "fastapi")),
    )
    res = client.post(
        "/api/matrix",
        json={
            "sources": [
                {"name": "evil", "url": url, "ref": "--upload-pack=touch /tmp/pwned"}
            ]
        },
    )
    evil = next(s for s in res.json()["sources"] if s["name"] == "evil")
    assert evil["ok"] is False and "invalid git ref" in evil["error"]


def test_api_token_guards_every_route_but_version(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AP_HOME", str(tmp_path / "home"))
    guarded = TestClient(build(token="s3cret"))

    assert guarded.get("/api/version").status_code == 200
    assert guarded.get("/api/apps").status_code == 401
    assert (
        guarded.get("/api/apps", headers={"authorization": "Bearer nope"}).status_code
        == 401
    )
    assert (
        guarded.get("/api/apps", headers={"authorization": "Bearer s3cret"}).status_code
        == 200
    )
