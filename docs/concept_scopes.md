# Scopes

A **scope** is where a release is deployed. It has a name, a kind, a criticality and a target. A release exists without any scope — it is a tag, cut from a branch — but a deployment never exists without one: *deploy release X to scope S*. Criticality is the rule that says which releases a scope may take.

Scopes replace the fixed `dev` / `prod` stages. Those two become the first two scopes of every app that already deploys; from then on an app has as many scopes as it needs, each with its own criticality.

## Why

- `dev` and `prod` say *where*, never *how much it matters*. A staging that a customer demos from and a scratch environment nobody depends on are both "dev" today, and get the same rules.
- The rule "a deploy ships a release" ([ADR 0002](adr/0002-targets-and-executors.md)) needs a second half: *which* release may reach *which* place. That half lives on the scope, as its criticality.
- Apps of different kinds deploy the same way but are operated differently: a web API, a scheduled job, a queue worker, a static site. The scope carries the kind so the platform can verify and diagnose each the right way.

## Definition

| Field | Meaning |
|---|---|
| `name` | unique within the app: `dev`, `staging`, `prod-eu`, `nightly-jobs` |
| `kind` | what runs there: `web` (answers HTTP), `job` (runs to completion on a schedule or a trigger), `worker` (consumes a queue), `static` (files behind a CDN), `library` (published to a registry, nothing runs) |
| `criticality` | `test` · `low` · `medium` · `high` · `critical` — see below |
| `target` | the deploy target and its options, as `[[deploy.targets]]` declares them today (`aws/lambda` + region, `docker` + registry, `pypi` + package…) |
| `run_by` | who executes deploys to it: `platform`, `github_actions`, `jenkins`, `manual` (unchanged from targets) |
| `url` | where the scope can be seen, when it has one |

An app has as many scopes as it needs, each with its own kind and criticality — nothing ties them to a ladder of names:

| App `orders-api` | kind | criticality | target |
|---|---|---|---|
| `dev` | web | test | aws/lambda us-east-1 |
| `staging` | web | low | aws/lambda us-east-1 |
| `prod-br` | web | high | aws/lambda sa-east-1 |
| `prod-eu` | web | critical | aws/lambda eu-west-1 |
| `nightly-reconcile` | job | low | aws/lambda us-east-1 |

Two scopes may share a criticality (`prod-br` and `prod-eu` could both be `critical`) and a criticality may be absent (an app with only `dev` and `prod`). The rules below read the app's scopes as they are.

A scope belongs to an app. Two apps never share a scope; an organization may define **scope presets** (name, kind, criticality) so every app creates the same `dev` / `staging` / `prod` with the same rules.

## Criticality

| Value | Name | Definition |
|---|---|---|
| `test` | Test | No production use. Nobody depends on it. |
| `low` | Low | Little impact; downtime is tolerable. |
| `medium` | Medium | Affects processes, but a manual alternative exists. |
| `high` | High | Affects important operations and many users. |
| `critical` | Critical | Essential to the business: stops operations, causes financial loss or legal risk. |

Criticality is ordered: `test < low < medium < high < critical`. Rules are written against that order, so a new level fits without touching the rules.

## What a scope accepts

Releases come in three shapes: **candidates** (`1.4.0-rc.2`, cut off `main`), **stable** (`1.4.0`, cut on `main`) and **hotfixes** (a release cut from a `hotfix/<code>` branch, which git-flow starts from `main`). Among stable releases of a component, one is the **latest**. The default policy:

| Criticality | Candidates | Stable | Must be latest | Hotfix |
|---|---|---|---|---|
| `test` | yes | no | — | yes |
| `low` | yes | yes | no | yes |
| `medium` | no | yes | yes | yes |
| `high` | no | yes | yes | yes |
| `critical` | no | yes | yes | yes |

In words:

- **A candidate is tried on `test` and `low`**; it never reaches `medium` or above.
- **A stable release goes to `low` and above**, never to `test` — `test` is where candidates are burned, and a stable release that needs a test run gets a candidate cut first.
- **From `medium` up only the latest stable release is deployed**: no rolling a `medium` scope forward to a version already superseded. Rollback is the exception — it names an older release and says so.
- **A hotfix goes anywhere**: production and every other level, whatever its shape and whether or not it is the latest — that is what a hotfix is for.

The policy is a table, not code. An organization may loosen or tighten it per criticality in Settings (or `[scopes.policy]` in `platform.toml` for one app) — for instance allow stable on `test`. The defaults above are what a new organization gets.

## Where the rules run

The gate that refuses a deploy already exists — [readiness](concept_deployments.md#readiness) blocks a release the checks failed. Scope policy adds **static checks** to the same list, computed from what the platform already knows (the release row, the deployment rows, the scope):

| Check | Blocks when |
|---|---|
| `scope.release-shape` | a candidate aims at `medium`+, or a stable release aims at `test`; never for a hotfix |
| `scope.latest` | `medium`+ and a newer stable release of the component exists; never for a hotfix |

They show on the release page like every other check, per scope instead of per stage, and the deploy form refuses the same way (`409`, `force` for `org.manage`).

## Relationship with what exists

| Today | With scopes |
|---|---|
| `stage` (`dev` \| `prod`) on deploy, readiness, deployment rows, the identity token | `scope` (name); the plugin still receives `ctx.stage = scope.name`, so `aws/lambda` keeps naming stacks `<prefix>-<scope>` |
| `[[deploy.targets]]` — *where* and *who* | becomes the scope's `target` and `run_by`; a target with `stages = [...]` is one scope per stage |
| readiness per (release, stage) | per (release, scope); the job runs for every scope of the app |
| `deployment.stage` | `deployment.scope_id` (+ `scope_name` kept for history) |
| `live_deploy(app, stage)` — one deploy at a time per stage | one at a time per scope |
| `AppIdentity` token carries `stage` | carries `scope` and `criticality`; the deploy proxy may grant by criticality (a `critical` scope gets a different boundary) |

A release stays what it is: a tag on the repository, one row in `release`, cut with no scope in mind. The row gains a `shape` — `candidate`, `stable` or `hotfix` — set when the platform cuts it: `hotfix` when the branch is `hotfix/*`, `candidate` for an `-rc.N` version, `stable` otherwise.

Open question: a release imported from the code host (not cut here) has no branch to read; its shape comes from the version alone (`candidate` or `stable`), so an imported hotfix is a `stable` until someone marks it.

## Kinds

The kind changes how the platform **verifies** and **diagnoses**, not how it deploys:

| Kind | Verify after deploy | Diagnose |
|---|---|---|
| `web` | `GET <url>/health` answers, version header or body matches | status, url, last error rate when the target exposes it |
| `job` | the job definition exists with the new version; last run status | next run, last run, duration |
| `worker` | the consumer is running with the new version | queue depth, consumers |
| `static` | the index at `<url>` carries the release marker | url, cache state |
| `library` | the version is at the registry (`pypi`, `npm`, `docker` already do this) | registry page |

`DeployTarget.verify(version, scope)` and `diagnose(ctx)` receive the scope, kind included; a target that does not know a kind says so and the scope refuses to be created with it.

## Data model

```
scope(id, app_id, name, kind, criticality, target_kind, target_options JSON,
      run_by, url, created_by, created_at)
      unique (app_id, name)
release.shape                  candidate | stable | hotfix
deployment.scope_id            (replaces stage; stage kept as scope_name for old rows)
release_readiness.scope_id     (replaces stage)
organization_setting scopes.policy     the policy table, when the organization changed it
organization_setting scopes.presets    the scopes a new app is created with
```

Migration: every app with `[deploy]` gets `dev` (`test`, `web`) and `prod` (`high`, `web`) from its current targets; deployment and readiness rows are re-pointed by stage name.

## API

```
GET    projects/{p}/apps/{a}/scopes                      the app's scopes with their policy verdict for the latest release
POST   projects/{p}/apps/{a}/scopes                      {name, kind, criticality, target, run_by, url}
PUT    projects/{p}/apps/{a}/scopes/{scope}
DELETE projects/{p}/apps/{a}/scopes/{scope}              refused while a deployment is live there
POST   apps/{id}/deploy {scope, version, dry_run, force}  scope replaces stage; stage still accepted and mapped to the scope of that name
GET    projects/{p}/apps/{a}/releases/{tag}/readiness    one row per scope
GET    organizations/settings/scopes                     policy and presets
PUT    organizations/settings/scopes
```

## Web

- **Scopes** section on the app (under Deployments): the table of scopes — name, kind, criticality badge, target, what is live there (version, verified, when), latest verdict — and **New scope**.
- **New deployment**: *Release* + *Scope* (replaces Environment); the readiness box explains the scope's verdict (`1.4.0-rc.1 cannot go to prod (medium): candidates stop at low`).
- **Releases › timeline**: readiness per scope; deployments grouped by scope.
- **Settings › Scopes**: the policy table with the defaults and the organization's overrides; presets.
- Criticality badge tones: `test` neutral, `low` neutral, `medium` warning, `high` danger outline, `critical` danger.

## CLI and MCP

```
action-platform scopes                              list
action-platform scope add prod-eu --kind web --criticality high --target aws/lambda --region eu-west-1
action-platform deploy --scope prod-eu --version 1.4.0
action-platform readiness --scope prod-eu --version 1.4.0
```

MCP: `list_scopes`, `create_scope`, `deploy` takes `scope`. `platform.toml` for a repository deploying on its own:

```toml
[[scopes]]
name = "dev"
kind = "web"
criticality = "test"
target = "aws/lambda"
region = "us-east-1"

[[scopes]]
name = "prod"
kind = "web"
criticality = "high"
target = "aws/lambda"
region = "us-east-1"
```

`[[deploy.targets]]` keeps working and reads as scopes named after the target (or its `stages`), criticality `test` for `dev` and `high` for `prod`, `low` for anything else.

## Rollout

1. **Model and policy** — `scope`, migration from stages, `ScopePolicy` in the library (`core/scopes.py`: criticality order, the default table, `eligible(release, scope, history) -> list[Check]`), tests. Deploy, readiness and deployment rows take `scope`; `stage` accepted and mapped. Nothing visible changes yet.
2. **Checks and gate** — the `scope.*` checks join readiness; the deploy gate reads them.
3. **Web** — Scopes table and New scope; the deploy form on scopes; readiness and timeline per scope; Settings › Scopes.
4. **Kinds** — `verify`/`diagnose` receive the scope; `aws/lambda` implements `web` and `job`; observed targets are `library`.
5. **CLI, MCP, `[[scopes]]`** in `platform.toml`; docs; `[[deploy.targets]]` documented as the short form.

Each step ships on its own; after step 1 the platform behaves as today.

## Decisions

- Scope belongs to the app, not the organization: two apps' `prod` differ in target and url; sharing would need a join table for nothing. Presets give the organization the consistency it wants.
- Criticality is on the scope, not on the release: a release does not know where it goes; the same `1.4.0` is harmless on `low` and a business risk on `critical`.
- The policy is data with defaults, not code: organizations differ on how strict `medium` is; the ladder (`test < low < medium < high < critical`) is the only thing fixed.
- Rules run as readiness checks: one gate, one place the user reads why a deploy is refused.
- `stage` survives as the plugin's view of a scope (`ctx.stage = scope.name`): no plugin changes for step 1, and stacks keep their names.

Related: [Deployments](concept_deployments.md) · [Releases](concept_releases.md) · [ADR 0002](adr/0002-targets-and-executors.md) · [ADR 0008](adr/0008-release-readiness.md) · [ADR 0009](adr/0009-scopes.md)
