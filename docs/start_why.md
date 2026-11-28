# Why Action Platform

What sets it apart, stated as behaviour you can check in the code and in these docs.

## Open source and self-hosted

The platform is licensed under Apache-2.0. You run it on your own server with one command (`install.sh`) or as a Dokploy compose service. Your repositories stay on your code host, your deploys land in your cloud account, and the database is yours. Nothing calls back to a vendor. [Self-hosting](start_self_hosting.md).

## A deploy always ships a release

A deployment names a tag, `vX.Y.Z` or `<component>/vX.Y.Z`. It never ships a branch or a working tree. The worker checks the tag out, builds that commit and deploys it, so what runs is always reproducible from the tag alone. Rolling back is deploying an older release. [Deployments](concept_deployments.md).

## It knows before you deploy

Right after a release is cut, the platform checks it against every scope of the app: the scope accepts the release shape, the manifests declare the tag's version, the credentials work, the deploy role has the permissions the template needs, the destination does not already hold that version. Nothing is built. A blocked release is refused unless the person deploying forces it, and the forced deploy is recorded like any other. After the deploy, the platform asks the destination whether the version arrived and marks the deployment **verified**. [Readiness](concept_deployments.md#readiness).

## Git-flow enforced in three places

Branch names are `<kind>/<code>`, commits are Conventional Commits, and `main`, `master` and `develop` take no direct commits. Git hooks refuse a wrong commit before it exists. CI refuses it on the pull request. On GitHub, GitLab and Bitbucket, the platform can set branch protection through the host's API and reports each rule the host's plan does not support. The CLI and the MCP tools pick the right base branch and pull request target for you. [Git-flow](concept_git_flow.md).

## AWS without access keys

The platform is an OpenID Connect issuer. To deploy to AWS Lambda, it signs a five-minute token about one app. AWS exchanges it for temporary credentials on the `ActionPlatformDeploy` role that a one-time, IAM-only stack creates in your account. A session tag limits each deploy to the stacks, functions, log groups and execution roles of its own app. No AWS key is stored on the platform, on a laptop or in a repository. [Cloud identity](concept_identity.md).

## One core, three surfaces

The web app, the CLI and the MCP server call the same library. An AI agent connected over MCP gets the same operations a person has, with the same git-flow rules, dry runs by default, and the permissions of the token it was given. [MCP](use_mcp.md).

## Templates in many languages

The official catalog covers web services (FastAPI, FastMCP, Gin, Fastify, React, Spring, Sinatra), libraries (Python, Go, PHP, Node, Java, Rust), automations, jobs, docs sites and a Chrome extension. Each ships tests, lint, CI for GitHub, GitLab, Jenkins or Bitbucket, and `AGENTS.md`. An organization adds its own repositories as templates. [Templates](concept_templates.md).

## Extensible with plain Python packages

Deploy targets, cloud overlays, readiness checks, MCP tools, CLI commands and access providers come from plugins: Python packages registered through entry points. AWS Lambda, Dokploy, Jenkins and Sentry ship this way. [Plugins](use_plugins.md), [Writing a plugin](contribute_plugins.md).

## It adopts what you already have

You do not start over. The platform imports a GitHub organization's repositories, adds `platform.toml`, hooks and quality config through one pull request per repository, keeps the CI each repository already runs, reads the release tags it already has, and records the deploys its existing Jenkins jobs or workflows make. [Adopting repositories](use_adopting.md).

## Limits to know

- Platform-run deploy targets today are AWS Lambda (`aws/lambda`) and Dokploy (`dokploy`), plus the package registries PyPI, npm, Docker, Packagist and Go. Other destinations are deployed by your CI and recorded by the platform, or need a plugin.
- The scope policy is fixed: `test` and `low` accept release candidates, `medium` and above accept only stable and hotfix releases.
- Readiness does not build. A green check does not prove the code compiles.
- On AWS, API Gateway and the SAM artifact bucket are shared within the account. Stacks, functions, layers, log groups and execution roles are per app.
