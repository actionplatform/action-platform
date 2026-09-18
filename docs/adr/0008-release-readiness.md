# 0008 — A release knows whether it can reach a stage before anyone deploys it

**Status**: accepted · 2026-09-18 · [#264](https://github.com/actionplatform/action-platform/issues/264)

## Context

Deploys failed for reasons knowable at release time: the deploy role could not read a public Lambda layer, a stack sat in `ROLLBACK_COMPLETE`, a manifest disagreed with the tag. Each surfaced minutes into a deploy, on the stage that mattered. Building every release to prove it deploys costs storage, toolchains and time, and still says nothing about permissions or the destination's state.

## Decision

Readiness is a set of checks a release passes or fails per stage, without building or changing anything. `DeployTarget.readiness(ctx) -> list[Check]` lets each target say what it can verify — credentials, permissions (simulated against the deploy role), stack state, template validity, a version already published. The core adds static checks: stage known, tag well-formed, manifests at the tag's version, lockfiles beside their manifests. A `Check` carries an id, a level (`static`, `target`, later `plan` and `proof`), a severity (`error` blocks, `warning` does not), a detail and a fix.

The platform runs the checks for `dev` and `prod` right after a release is cut here, on the deploy worker, and stores the verdict per release and stage in `release_readiness`. Releases show it, the release page lists the checks, the deploy form loads it for the chosen release and stage, and the API refuses a deploy whose readiness for that stage is blocked unless the request says `force`. A release never checked passes: the gate only trusts what it verified.

## Consequences

Permission, state and configuration failures move from the deploy to the release, where they are cheap. Compilation is still unproven — a green readiness is not a build. The `plan` (change set, dry build) and `proof` (deploy to dev and verify) levels are named but not run yet. Every target that wants a say implements `readiness`; those that do not are checked statically only. Existing proxies need redeploying to grant `iam:SimulatePrincipalPolicy` to the deploy role.
