import { type Grants } from "@/lib/permissions";
import { notFound } from "next/navigation";
import { cache } from "react";
import { api, ApiError, type Release } from "@/lib/api";
import { releasesOf, type StoredRelease } from "@/lib/releases";
import { appById, projectById } from "@/lib/projects";

import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { type AppView, toView } from "./model";

export type Host = { id: string; name: string; kind: string; defaultOwner: string | null };

export type Loaded =
  | { ok: true; view: AppView; hosts: Host[]; currentHost: string | null; releases: Release[]; stored: StoredRelease[] }
  | { ok: false; name: string; projectId: string; reason: string | null };

export const loadApp = cache(async (projectId: string, appId: string): Promise<Loaded> => {
  const { session, org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  if (!project) notFound();
  const app = await appById(projectId, appId);
  if (!app) notFound();

  try {
    const [detail, health, commits, branches, tags, hosts, releases, stored, manifest, rules] = await Promise.all([
      api.apps.get(app.registryId),
      api.apps.gitflow(app.registryId),
      api.apps.commits(app.registryId, 50),
      api.apps.branches(app.registryId),
      api.apps.tags(app.registryId),
      hostsOf(org.id),
      api.apps.releases(app.registryId),
      releasesOf(projectId, app.id),
      api.apps.manifest(app.registryId),
      api.gitflowRules(),
    ]);
    const changes = detail.clean ? [] : (await api.apps.changes(app.registryId).catch(() => ({ files: [] as string[] }))).files;
    const view = toView({ projectId, projectName: project.name, projectSlug: project.slug, orgSlug: org.slug, appId: app.id, appName: app.name, detail, health, commits, branches, tags, lastSyncedAt: app.lastSyncedAt, manifest: manifest.content, manifestMirrored: manifest.mirrored ?? true, changes, grants: session.grants as Grants, rules: { kinds: rules.kinds, protected: rules.protected } });
    return { ok: true, view, hosts: hosts.map((h) => ({ id: h.id, name: h.name, kind: h.kind, defaultOwner: h.defaultOwner })), currentHost: app.sourceHostId, releases, stored };
  } catch (e) {
    if (e instanceof ApiError && e.status === 410) notFound();
    return { ok: false, name: app.name, projectId, reason: e instanceof Error ? e.message : null };
  }
});
