from action_platform.settings import database_url_from_parts, secret


def test_secret_prefers_file(tmp_path, monkeypatch):
    path = tmp_path / "token"
    path.write_text("from-file\n")
    monkeypatch.setenv("AP_API_TOKEN_FILE", str(path))
    monkeypatch.setenv("AP_API_TOKEN", "from-env")

    assert secret("AP_API_TOKEN") == "from-file"


def test_secret_falls_back_across_names(monkeypatch):
    monkeypatch.delenv("AP_AUTH_SECRET", raising=False)
    monkeypatch.delenv("AP_AUTH_SECRET_FILE", raising=False)
    monkeypatch.setenv("BETTER_AUTH_SECRET", "legacy")

    assert secret("AP_AUTH_SECRET", "BETTER_AUTH_SECRET") == "legacy"


def test_secret_skips_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AP_API_TOKEN_FILE", str(tmp_path / "missing"))
    monkeypatch.setenv("AP_API_TOKEN", "from-env")

    assert secret("AP_API_TOKEN") == "from-env"


def test_database_url_from_parts(tmp_path, monkeypatch):
    path = tmp_path / "pw"
    path.write_text("p@ss:word")
    monkeypatch.setenv("AP_DB_HOST", "db")
    monkeypatch.setenv("AP_DB_PASSWORD_FILE", str(path))
    monkeypatch.delenv("AP_DB_PASSWORD", raising=False)

    assert (
        database_url_from_parts()
        == "postgres://action_platform:p%40ss%3Aword@db:5432/action_platform"
    )


def test_database_url_needs_host(monkeypatch):
    monkeypatch.delenv("AP_DB_HOST", raising=False)

    assert database_url_from_parts() == ""
