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

Off `main`/`master` the release is a pre-release `X.Y.Z-rc.N` (GitHub marks it prerelease; publish workflows send it to the test index). Say so when the user is on a feature or develop branch. A dirty working tree fails the release; tell the user to commit first rather than committing for them. The release commit (`chore(release): X.Y.Z`) is the only non-bootstrap commit the hooks accept on `main`/`develop`; run it from the branch the user releases from — usually `main`, or `develop` on a git-flow release branch.
