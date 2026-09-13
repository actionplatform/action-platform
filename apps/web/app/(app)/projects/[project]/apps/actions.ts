"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import { appById, createApp, deleteApp, markSynced, projectById, setAppHost } from "@/lib/projects";
import { requirePermission } from "@/lib/orgs";
import type { Permission } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { syncPullRequests } from "@/lib/pull-requests";
import { syncReleases } from "@/lib/releases";
import { credentialsFor, hostsOf } from "@/lib/source-hosts";
import { sourceSpecByName } from "@/lib/template-sources";

async function owned(projectId: string, permission: Permission) {
  const { session, org } = await requireOrg();
  await requirePermission(session.user.id, org.id, permission);
  const project = await projectById(org.id, projectId);
  if (!project) throw new Error("project not found");
  return { org, project };
}

async function credsFor(orgId: string, projectId: string, appId: string) {
  const app = await appById(projectId, appId);
  if (!app?.sourceHostId) return null;
  return credentialsFor(orgId, app.sourceHostId);
}

function repoOf(url: string, fromToml: string | null | undefined): string | null {
  if (fromToml) return fromToml;
  const m = url.match(/[:/]([^/:]+\/[^/]+?)(?:\.git)?$/);
  return m ? m[1] : null;
}

function kindOf(url: string): string | null {
  if (url.includes("github.com")) return "github";
  if (url.includes("gitlab")) return "gitlab";
  if (url.includes("bitbucket.org")) return "bitbucket";
  return null;
}

async function hostFor(orgId: string, url: string) {
  const kind = kindOf(url);
  const hosts = await hostsOf(orgId);
  return hosts.find((h) => h.kind === kind) ?? null;
}

export async function pullReleases(projectId: string, appId: string) {
  const { org } = await owned(projectId, "app.sync");
  const app = await appById(projectId, appId);
  if (!app) return { ok: false as const, error: "app not found" };
  const detail = await api.apps.get(app.registryId);
  const repo = repoOf(detail.url, detail.source_host.repo);
  const [releases] = await Promise.all([syncReleases(org.id, app.id, app.sourceHostId, repo), syncPullRequests(org.id, app.id, app.sourceHostId, repo)]);
  return releases;
}

export type AddResult = { ok: true; appId: string; installed: string[] | null } | { ok: false; error: string; needsInstall?: boolean };

export async function addApp(projectId: string, url: string, install: { type: string; ci: string } | null = null): Promise<AddResult> {
  url = url.trim();
  if (!url) return { ok: false, error: "url is required" };
  try {
    const { org } = await owned(projectId, "project.manage");
    const host = await hostFor(org.id, url);
    const credentials = host ? await credentialsFor(org.id, host.id) : null;
    const kind = kindOf(url);
    if (kind && !credentials) return { ok: false, error: `No ${kind} host is connected to this organization. Connect one in Settings so private repositories can be cloned.` };
    const entry = await api.apps.add(url, undefined, credentials, install);
    const app = await createApp(projectId, entry.id, entry.name, host?.id ?? null);
    if (host) await Promise.all([syncReleases(org.id, app.id, host.id, repoOf(url, null)), syncPullRequests(org.id, app.id, host.id, repoOf(url, null))]);
    revalidatePath(`/projects/${projectId}`);
    return { ok: true, appId: app.id, installed: entry.installed ?? null };
  } catch (e) {
    if (e instanceof ApiError && e.code === "needs_install") return { ok: false, error: e.message, needsInstall: true };
    return { ok: false, error: (e as Error).message };
  }
}

export async function removeApp(projectId: string, appId: string) {
  await owned(projectId, "project.manage");
  const app = await deleteApp(projectId, appId);
  if (app) await api.apps.remove(app.registryId).catch(() => {});
  revalidatePath(`/projects/${projectId}`);
}

export async function syncApp(projectId: string, appId: string, registryId: string): Promise<{ ok: true } | { ok: false; error: string }> {
  const { org } = await owned(projectId, "app.sync");
  try {
    await api.apps.sync(registryId, await credsFor(org.id, projectId, appId));
  } catch (e) {
    return { ok: false, error: (e as Error).message || "sync failed" };
  }
  await pullReleases(projectId, appId);
  await markSynced(projectId, appId);
  revalidatePath(`/projects/${projectId}`, "layout");
  return { ok: true };
}

export async function previewRelease(registryId: string, level: string, branch: string | null = null) {
  const { session, org } = await requireOrg();
  await requirePermission(session.user.id, org.id, "app.release");
  return api.apps.release(registryId, level, true, null, branch);
}

export async function runRelease(projectId: string, appId: string, registryId: string, level: string, branch: string | null = null) {
  const { org } = await owned(projectId, "app.release");
  const result = await api.apps.release(registryId, level, false, await credsFor(org.id, projectId, appId), branch);
  await pullReleases(projectId, appId);
  revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

export async function pushApp(projectId: string, appId: string, registryId: string, priv: boolean, sourceHostId: string | null): Promise<{ ok: true; url: string } | { ok: false; error: string }> {
  const { org } = await owned(projectId, "app.flow");
  try {
    if (sourceHostId) await setAppHost(projectId, appId, sourceHostId);
    const creds = sourceHostId ? await credentialsFor(org.id, sourceHostId) : await credsFor(org.id, projectId, appId);
    if (!creds) return { ok: false, error: "pick a source host first (Settings → Source hosts)" };
    const r = await api.apps.push(registryId, priv, creds);
    await pullReleases(projectId, appId);
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, url: r.url };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

type Result<T> = { ok: true; data: T } | { ok: false; error: string };

export async function startBranch(projectId: string, appId: string, registryId: string, input: { kind: string; code: string; slug: string; push: boolean }): Promise<Result<{ branch: string; base: string; pushed: boolean }>> {
  const { org } = await owned(projectId, "app.flow");
  try {
    const data = await api.apps.startBranch(registryId, { ...input, slug: input.slug || null, credentials: input.push ? await credsFor(org.id, projectId, appId) : null });
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function checkoutBranch(projectId: string, registryId: string, branch: string): Promise<Result<{ branch: string }>> {
  await owned(projectId, "app.flow");
  try {
    const data = (await api.apps.checkout(registryId, branch)) as { branch: string };
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function proposePullRequest(projectId: string, registryId: string): Promise<Result<{ head: string; base: string; title: string; body: string; commits: string[] }>> {
  await owned(projectId, "app.flow");
  try {
    return { ok: true, data: await api.apps.proposePullRequest(registryId) };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function openPullRequest(projectId: string, appId: string, registryId: string, input: { base: string; title: string; body: string; draft: boolean }): Promise<Result<{ number: number; url: string }>> {
  const { org } = await owned(projectId, "app.flow");
  try {
    const data = await api.apps.openPullRequest(registryId, { ...input, credentials: await credsFor(org.id, projectId, appId) });
    await pullReleases(projectId, appId);
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function saveManifest(projectId: string, registryId: string, content: string): Promise<Result<{ content: string }>> {
  await owned(projectId, "app.configure");
  try {
    const data = await api.apps.writeManifest(registryId, content);
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function setCloudTarget(projectId: string, registryId: string, target: string, source: string | null = null): Promise<Result<{ target: string }>> {
  const { org } = await owned(projectId, "app.configure");
  try {
    const data = (await api.apps.setCloud(registryId, target, await sourceSpecByName(org.id, source))) as { target: string };
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function addService(projectId: string, registryId: string, name: string, provider: string | null, source: string | null = null): Promise<Result<{ name: string }>> {
  const { org } = await owned(projectId, "app.configure");
  try {
    const data = (await api.apps.addService(registryId, name, provider, await sourceSpecByName(org.id, source))) as { name: string };
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export type CommitInput = { message: string; push: boolean; branch: { kind: string; code: string; slug: string } | null; pullRequest: boolean };

export async function commitChanges(projectId: string, appId: string, registryId: string, input: CommitInput): Promise<Result<{ sha: string; branch: string; pushed: boolean; pull_request?: { number: number; url: string } | null }>> {
  const { org } = await owned(projectId, "app.configure");
  const remote = input.push || input.pullRequest;
  try {
    const data = await api.apps.commit(registryId, {
      message: input.message,
      push: input.push,
      branch: input.branch ? { kind: input.branch.kind, code: input.branch.code, slug: input.branch.slug || null } : null,
      pull_request: input.pullRequest,
      credentials: remote ? await credsFor(org.id, projectId, appId) : null,
    });
    if (data.pull_request) await pullReleases(projectId, appId);
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}
