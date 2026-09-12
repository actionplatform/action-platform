# Changelog

## v0.1.9 — 2026-09-12

### Features
- the Action Platform logo — favicon, sidebar, auth and setup pages, README

## v0.1.8 — 2026-09-12

### Features
- **web:** disconnect a connected account and remove an OAuth app

## v0.1.7 — 2026-09-12

### Bug Fixes
- **web:** accept the GitHub App install callback without state; login honours next

## v0.1.6 — 2026-09-12

### Bug Fixes
- **web:** external URLs come from PUBLIC_URL, not the container's request origin

## v0.1.5 — 2026-09-12

### Bug Fixes
- **web:** trust both schemes of the public host

## v0.1.4 — 2026-09-12

### Features
- **web:** create the GitHub App through the manifest flow — no manual OAuth app

### Chores
- strip comments from source, configs and workflows; nextCookies last

## v0.1.3 — 2026-09-12

### Bug Fixes
- **web:** run boot migrations once — in-flight promise and advisory lock
- **web:** add public/ (robots.txt) so the image build has it

## v0.1.2 — 2026-09-12

## v0.1.1 — 2026-09-12

### Features
- **web:** setup wizard, organizations › projects › apps, create-app wizard, templates catalog, code hosts, device approval
- **web:** monochrome design system — primitives, dialogs, sidebar with org switcher, brand icons
- **web:** multi-engine db (sqlite/pg/mysql), runtime config, auth with orgs/device/bearer, encrypted source hosts, oauth
- **web:** login, projects, project detail with release/deploy panels, templates, settings
- **web:** UI primitives, sidebar, page header, user menu, api-offline banner
- **web:** typed API client from OpenAPI, auth and db wiring

### Refactoring
- **core:** split into manifest, scaffold, flow and release packages; providers/source registry

### Docs
- web app and platform README — self-host, hierarchy, layout
- apps/web README and the browser section in the main README

### Build
- **web:** tailwind v4, simple-icons, better-auth plugins, per-engine drizzle configs, standalone output
- **web:** Next.js 15 app in apps/web — Tailwind v4, drizzle, better-auth, openapi-typescript

### Chores
- **platform:** declare web and api release components
- **web:** ignore tsbuildinfo
