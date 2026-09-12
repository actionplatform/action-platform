# Changelog

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
