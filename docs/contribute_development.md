# Development

## Python

```bash
poetry install --extras mcp
poetry run pip install -e apps/api httpx httpx2  # the API package, editable, on top of the library
poetry run pytest -q                      # the library; or: python -m unittest discover -s tests -t .
(cd apps/api && ../../.venv/bin/python -m pytest -q)   # the API
poetry run ruff check . && poetry run ruff format --check .
AP_ALLOW_UNAUTHENTICATED=1 poetry run action-platform-api serve --reload   # :7788, OpenAPI at /docs; without a token the API refuses to start unless told so
```

Tests use throwaway git repositories and a tiny templates index under `tmp_path`; nothing touches the network or the user's home.

## Web

```bash
cd apps/web
npm install
npm run dev            # :3000
npx tsc --noEmit
npm run api:types      # regenerate lib/api.d.ts from the Python app (no server needed)
```

The web app keeps no state: it needs `AP_API` (where the API listens) and `PUBLIC_URL`. Everything the wizard creates lands in the API's database (`AP_DATABASE_URL`); point it at a fresh SQLite file to start over.

Rules that come from mistakes already made:

- Never use `window.confirm` / `prompt` / `alert`; use `components/ui/dialog.tsx`.
- Client components must not import modules that call the API (`lib/api`, `lib/v1`, `lib/orgs`, `lib/source-hosts`, `lib/oauth`); shared types and constants live in `lib/types.ts`, `lib/permissions.ts` and `lib/source-host-kinds.ts`.
- Do not run `npm run build` while `npm run dev` is running — both write `.next/`.

## Repository conventions

Git-flow and Conventional Commits, enforced by the hooks `action-platform install` puts in `.git/hooks` and by CI. Work on `<kind>/<code>` branches, open a pull request, never commit on `master`. Releases are cut from `master` with `action-platform release [--component web|api]`; each component publishes on its own tag (see [releases](concept_releases.md)).

## Tests

`tests/` mirrors the package: `tests/core/flow/test_branching.py` and `test_pullrequest.py` cover `action_platform/core/flow/workflow.py` (`GitFlow`), `tests/core/flow/test_git.py` covers the policies in `git.py`, `apps/api/tests/services/test_flow.py` covers `apps/api/services/workspace/flow.py`, and so on. Every module is a set of `unittest.TestCase` classes, one per behaviour group; pytest is only the runner. Shared builders live in `action_platform/testing/fixtures.py` (re-exported by `tests/support.py`) (`TempCase` with a temporary directory and an isolated environment, `git()`, `repo_with_origin()`, `platform_repo()`, `template_repo()`), `apps/api/tests/support.py` (`ApiCase`: a `TestClient` over a fresh API with a platform project reachable as `file://`) and `tests/mcp/support.py` (`McpCase`: a local server over a tiny templates index).
