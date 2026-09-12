# Development

## Python

```bash
poetry install --extras api --extras mcp
poetry run pytest -q
poetry run ruff check action_platform tests && poetry run ruff format --check action_platform tests
poetry run action-platform api --reload      # :7788, OpenAPI at /docs
```

Tests use throwaway git repositories and a tiny templates index under `tmp_path`; nothing touches the network or the user's home.

## Web

```bash
cd apps/web
npm install
npm run dev            # :3000
npx tsc --noEmit
npm run api:types      # regenerate lib/api.d.ts from the Python app (no server needed)
npm run db:generate    # one migration per engine after editing lib/db/schema/*.ts
```

State written by the wizard lives in `apps/web/config/app.json` and, for SQLite, `apps/web/data/`; both are gitignored — delete them to start over.

Rules that come from mistakes already made:

- Never use `window.confirm` / `prompt` / `alert`; use `components/ui/dialog.tsx`.
- Client components must not import modules that pull `node:*` (`lib/db`, `lib/orgs`, `lib/source-hosts`, `lib/crypto`, `lib/oauth`); shared types and constants live in `lib/types.ts` and `lib/source-host-kinds.ts`.
- Do not run `npm run build` while `npm run dev` is running — both write `.next/`.

## Repository conventions

Git-flow and Conventional Commits, enforced by the hooks `action-platform install` puts in `.git/hooks` and by CI. Work on `<kind>/<code>` branches, open a pull request, never commit on `master`. Releases are cut from `master` with `action-platform release [-c web|api]`.
