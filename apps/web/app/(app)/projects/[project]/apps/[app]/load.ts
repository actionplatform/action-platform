import { notFound } from "next/navigation";
import { cache } from "react";
import { api, ApiError, type Release } from "@/lib/api";
import { releasesOf, type StoredRelease } from "@/lib/releases";
import { appById, projectById } from "@/lib/projects";
import { roleOf } from "@/lib/orgs";
import { grantsOf } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { hostsOf } from "@/lib/source-hosts";
import { type AppView, toView } from "./model";

export type Host = { id: string; name: string; kind: string; defaultOwner: string | null };

export type Loaded =
  | { ok: true; view: AppView; hosts: Host[]; currentHost: string | null; releases: Release[]; stored: StoredRelease[] }
  | { ok: false; name: string; projectId: string; registryId: string; reason: string | null; missingManifest: boolean };

export const loadApp = cache(async (projectId: string, appId: string): Promise<Loaded> => {
  const { session, org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  if (!project) notFound();
  const app = await appById(projectId, appId);
  if (!app) notFound();

  try {
    const [detail, health, commits, branches, tags, hosts, releases, stored, manifest] = await Promise.all([
      api.apps.get(app.registryId),
      api.apps.gitflow(app.registryId),
      api.apps.commits(app.registryId, 50),
      api.apps.branches(app.registryId),
      api.apps.tags(app.registryId),
      hostsOf(org.id),
      api.apps.releases(app.registryId),
      releasesOf(app.id),
      api.apps.manifest(app.registryId),
    ]);
    const changes = detail.clean ? [] : (await api.apps.changes(app.registryId).catch(() => ({ files: [] as string[] }))).files;
    const view = toView({ projectId, projectName: project.name, appId: app.id, appName: app.name, detail, health, commits, branches, tags, lastSyncedAt: app.lastSyncedAt, manifest: manifest.content, changes, grants: grantsOf(await roleOf(session.user.id, org.id)) });
    return { ok: true, view, hosts: hosts.map((h) => ({ id: h.id, name: h.name, kind: h.kind, defaultOwner: h.defaultOwner })), currentHost: app.sourceHostId, releases, stored };
  } catch (e) {
    if (e instanceof ApiError && e.status === 410) notFound();
    const reason = e instanceof Error ? e.message : null;
    return { ok: false, name: app.name, projectId, registryId: app.registryId, reason, missingManifest: !!reason && reason.includes("platform.toml") };
  }
});
