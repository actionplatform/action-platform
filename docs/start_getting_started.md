# Getting started

Two ways in: the CLI on your machine, or a hosted platform in the browser with the CLI and MCP logged in to it. Both use the same core, the same `platform.toml`, the same git-flow.

## Install

```bash
pipx install action-platform            # library + CLI
pip install "action-platform[mcp]"      # + MCP server for Claude Code, Codex, Cursor
pip install ./apps/api      # + the JSON API (only for self-hosting)
```

Needs `git` and, for the source host, either the `gh` CLI or a token (`ACTION_PLATFORM_GITHUB_TOKEN`, `ACTION_PLATFORM_GITLAB_TOKEN`, `ACTION_PLATFORM_BITBUCKET_TOKEN` + `_USERNAME`).

## First project, locally

```bash
action-platform init                    # type → stack → template → name → ci; creates the repository and pushes
cd <name>
action-platform branch feature 1 hello  # develop (or main) → feature/1-hello, hooks installed
git commit -m "feat: say hello"         # the hooks refuse a message that is not Conventional Commits
action-platform pr                      # target from the rules, body from the commits
action-platform release --dry-run       # shows the next version and changelog; drop --dry-run on main to publish
```

Bring an existing repository in with `action-platform install` instead of `init`: it adds `platform.toml`, `LAST_VERSION` (from the newest `vX.Y.Z` tag, or `0.0.0`), `AGENTS.md`, the quality config, the CI files and the hooks, never overwriting a file you have.

## First project, hosted

1. Sign in to the platform, create an organization, connect a source host (Settings → *Connect a code host*).
2. **New app** from a template, or *Add an existing repository* with its URL — the platform clones it and installs the files above when they are missing; **Commit changes** opens the pull request.
3. **Release** from the app page; the branch decides stable (`main`/`master`) or `-rc.N`.

Point the CLI and an AI agent at it:

```bash
action-platform login https://<platform> --scope read,write   # approve the code in the browser, choose where the token may act
action-platform whoami
action-platform mcp --remote                                   # the same tools, acting on the hosted apps
```

What a token may do is your role narrowed by its scope and reach — [access control](concept_access_control.md).

## Next

[CLI](use_cli.md) for every command · [web](use_web.md) for every screen · [MCP](use_mcp.md) for agents · [manifest](concept_manifest.md) for `platform.toml` · [self-hosting](start_self_hosting.md) to run your own.
