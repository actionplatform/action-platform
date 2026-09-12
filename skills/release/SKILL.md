---
name: release
description: Cut a version: preview next version and changelog with a dry run, then publish only on approval.
---

# Releasing

`release` defaults to `dry_run=true`. That is the preview; the real call is a second step.

1. `project_info` to confirm which project.
2. `release` with the level the user asked for (`patch` unless said otherwise). Show `next` and the `changelog`.
3. Empty changelog or wrong bump means the commits do not follow Conventional Commits — say so and stop.
4. On approval, `release` again with `dry_run=false`. Report the tag.

A dirty working tree fails the release; tell the user to commit first rather than committing for them.
