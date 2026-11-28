# Quickstart

Create a project from a template, push it to GitHub, open a pull request through git-flow and cut its first release. All from the terminal, in a few minutes, with no server to run.

## Prerequisites

- Python 3.10 or newer and [pipx](https://pipx.pypa.io/).
- `git`, with `user.name` and `user.email` set.
- A GitHub account, with the [`gh` CLI](https://cli.github.com/) signed in (`gh auth login`), or a token in `ACTION_PLATFORM_GITHUB_TOKEN`. GitLab and Bitbucket work too: `ACTION_PLATFORM_GITLAB_TOKEN`, or `ACTION_PLATFORM_BITBUCKET_TOKEN` with `ACTION_PLATFORM_BITBUCKET_USERNAME`.

## 1. Install the CLI

```bash
pipx install "action-platform[mcp]"
action-platform --help
```

The `mcp` extra adds the MCP server for AI agents. Leave it out if you only want the CLI.

## 2. Create a project

List the templates, then create a FastAPI service with GitHub Actions:

```bash
action-platform init --list
action-platform init web python fastapi --name hello --ci github
cd hello
```

`init` asks for anything you leave out (the licence, the repository owner). It renders the template, creates a private repository on GitHub and pushes `main`. Add `--no-push` to keep it local, `--public` for a public repository.

**Result:** a repository with the application, tests, lint config, CI workflows, `platform.toml`, `LAST_VERSION` and `AGENTS.md`.

## 3. Start a branch

```bash
action-platform branch feature 1 hello
```

This installs the git hooks, picks the base branch (`develop`, or `main` when there is no `develop`), pulls it and creates `feature/1-hello`.

## 4. Commit through the hooks

Make a change, then commit with a message that is not a Conventional Commit:

```bash
git commit -am "say hello"
```

The `commit-msg` hook refuses it. Commit again with a valid message:

```bash
git commit -am "feat: say hello"
action-platform gitflow
```

`gitflow` audits the branch name and every commit since the branch left its base.

## 5. Open a pull request

```bash
action-platform pr --dry-run
action-platform pr
```

The dry run shows the target branch, the title and the body built from the commits. The second command opens the pull request. Merge it on GitHub; the CI checks `gitflow` and `conventional-commit` run on it.

## 6. Cut the first release

```bash
git checkout main && git pull
action-platform release minor --dry-run
action-platform release minor
```

The dry run prints the next version, `0.1.0` for a repository without tags, and the changelog generated from the commits. The second command writes `LAST_VERSION` and `CHANGELOG.md`, commits `chore(release): 0.1.0`, tags `v0.1.0`, pushes and publishes the release on GitHub. On any branch other than `main` or `master`, `release` cuts a candidate `X.Y.Z-rc.N` instead.

**Result:** release `v0.1.0` on GitHub with its changelog.

## Next steps

- **Deploy it.** Add a cloud overlay and scopes, then deploy a release: [Deploy from the web](guide_first_deploy.md) on a hosted platform, or [Deploy to AWS Lambda](guide_aws_lambda.md) from the terminal.
- **Bring an existing repository.** Run `action-platform install` in it instead of `init`: [Adopting repositories](use_adopting.md).
- **Use an AI agent.** Run `action-platform mcp` and connect Claude Code, Codex or Cursor: [MCP](use_mcp.md).
- **Learn the model.** [Core concepts](start_concepts.md).
