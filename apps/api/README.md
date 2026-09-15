# action-platform-api

The hosted platform: accounts, organizations, projects, apps, jobs and code-host connections, served over the `action-platform` library.

```bash
poetry install
AP_DATABASE_URL=postgres://… action-platform-api serve          # http://127.0.0.1:7788
action-platform-api worker                                        # runs queued jobs
action-platform-api db upgrade
```

Tests: `poetry run pytest`. Lint: `poetry run ruff check .` and `poetry run ruff format --check .`.

See [docs/use_api.md](../../docs/use_api.md) and [docs/start_self_hosting.md](../../docs/start_self_hosting.md).
