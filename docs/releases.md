# Releases

One repository, three artifacts, three versions.

| Component | Path | Command | Tag | Publishes |
|---|---|---|---|---|
| library + CLI (root) | `.` | `action-platform release minor` | `v0.3.0` | `action-platform` on PyPI |
| api | `action_platform/api` | `action-platform release -c api patch` | `api/v0.1.2` | `actionplatformio/action-platform-api` (Docker Hub + GHCR) |
| web | `apps/web` | `action-platform release -c web minor` | `web/v0.2.0` | `actionplatformio/action-platform-web` (Docker Hub + GHCR) |

Declared in `platform.toml`:

```toml
[components.web]
path = "apps/web"

[components.api]
path = "action_platform/api"
```

## What a release does

1. Refuses a dirty tree, a version that already exists, a tag that exists locally or on `origin`.
2. Computes the next version from `<path>/LAST_VERSION`. Off `main`/`master` (or with `--rc`) it is `X.Y.Z-rc.N`, counting only that component's tags.
3. Renders the changelog from Conventional Commits since the component's last tag, limited to commits that touched `path`; the root excludes every component path.
4. Writes `LAST_VERSION`, prepends `CHANGELOG.md`, syncs `package.json` / `pyproject.toml` / `__version__` under `path`.
5. Commits `chore(release): [<name> ]X.Y.Z`, tags, pushes both, publishes the release on the source host (pre-release when rc).

`--dry-run` stops after step 3 and prints the version and changelog.

## Workflows

| Workflow | Trigger | Does |
|---|---|---|
| `python-publish-pypi.yml` | release published for `vX.Y.Z` (skips `*/v*`) | builds and uploads to PyPI through a Trusted Publisher (environment `pypi`) |
| `images.yml` | tag `api/v*` or `web/v*`, or manual dispatch with a component | builds `deploy/Dockerfile.<component>`, pushes `:X.Y.Z` (and `:latest` for stable) to Docker Hub and GHCR |
| `code-quality.yml`, `conventional-commit.yml`, `gitflow.yml`, `trivy.yml` | pull requests and pushes | the shared checks from ci-scripts |

Secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (read & write); variable `DOCKERHUB_NAMESPACE` when the Hub account is not `actionplatformio`. GHCR uses `GITHUB_TOKEN`.

## Compatibility

The web app's API client is generated from the API's OpenAPI schema. Ship `api` and `web` together when the contract changes; a web image older than the API it talks to may miss fields, never the other way round is guaranteed.
