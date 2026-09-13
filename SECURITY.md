# Security Policy

## Supported Versions

Every component ships from `master` and is versioned on its own. Only the latest release of each receives security fixes:

| Component | Tag | Supported |
| --- | --- | --- |
| CLI / MCP server (`action-platform` on PyPI) | `vX.Y.Z` | latest `0.x` release |
| API image (`actionplatformio/action-platform-api`) | `api/vX.Y.Z` | latest release, `:latest` |
| Web image (`actionplatformio/action-platform-web`) | `web/vX.Y.Z` | latest release, `:latest` |
| Older releases | — | no security updates |

A self-hosted platform on `:latest` with `pull_policy: always` picks up a fix on its next redeploy; the CLI with `pipx upgrade action-platform`.

## Security Updates

Security fixes are released as soon as possible after a vulnerability is confirmed, as a patch release of the affected component, with the fix described in the release notes once a fixed version is available.

## Reporting a Vulnerability

If you discover a security vulnerability:

1. **Do not** disclose it publicly — no issue, discussion or pull request.
2. Send a report to `security@actionplatform.io`, or open a private advisory at https://github.com/actionplatform/action-platform/security/advisories/new.
3. Include:
   - a description of the vulnerability
   - steps to reproduce
   - the potential impact
   - the component and version (`action-platform --version`; Settings shows the API version)

You will get an acknowledgement within 72 hours. We work with you on a fix and coordinate the disclosure date; credit goes to the reporter unless you prefer otherwise.

## Scope

In scope: this repository (CLI, API, web app, MCP server, deploy files), [templates](https://github.com/actionplatform/templates), [ci-scripts](https://github.com/actionplatform/ci-scripts) and the CI wrappers, and the published images and package.

Out of scope: vulnerabilities in the code hosts, clouds or CI systems the platform talks to; issues in a self-hosted instance caused by its own configuration (exposed database, missing `AP_API_TOKEN`, HTTP without TLS); denial of service against a demo instance.

## What the platform does on your behalf

Worth knowing when you assess a report:

- The API clones repositories and runs `git` and template hooks for every app; it must only be reachable by the web app (`AP_API_TOKEN`, private network). See [Self-hosting](docs/start_self_hosting.md).
- Code-host tokens are stored encrypted in the web app's database and travel to the API per request; they never land on disk on the API side. See [Architecture](docs/contribute_architecture.md).
- Template repositories added by an organization run their cookiecutter hooks on the platform: only add repositories you trust.
