"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { api, ApiError, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

function refresh(projectId: string) {
  revalidatePath(`/projects/${projectId}`, "layout");
}

export async function pullReleases(projectId: string, appId: string): Promise<{ ok: true; count: number } | { ok: false; error: string }> {
  await requireOrg();
  try {
    const imports = await v1.syncImports(projectId, appId);
    const error = imports.errors?.releases;
    return error ? { ok: false, error } : { ok: true, count: imports.releases.length };
  } catch (e) {
    return failed(e);
  }
}

export type AddResult = { ok: true; appId: string; installed: string[] | null } | { ok: false; error: string; needsInstall?: boolean };

export async function addApp(projectId: string, url: string, install: { type: string; ci: string; language: string | null } | null = null): Promise<AddResult> {
  url = url.trim();
  if (!url) return { ok: false, error: "url is required" };
  await requireOrg();
  try {
    const app = await v1.addApp(projectId, url, install);
    revalidatePath(`/projects/${projectId}`);
    return { ok: true, appId: app.id, installed: app.installed ?? null };
  } catch (e) {
    if (e instanceof ApiError && e.code === "needs_install") return { ok: false, error: e.message, needsInstall: true };
    return failed(e);
  }
}

export async function removeApp(projectId: string, appId: string) {
  await requireOrg();
  await v1.deleteApp(projectId, appId);
  revalidatePath(`/projects/${projectId}`);
}

export async function syncApp(projectId: string, appId: string, registryId: string): Promise<{ ok: true } | { ok: false; error: string }> {
  await requireOrg();
  try {
    await api.apps.sync(registryId);
    await v1.syncImports(projectId, appId).catch(() => null);
    refresh(projectId);
    return { ok: true };
  } catch (e) {
    return failed(e, "sync failed");
  }
}

export async function previewRelease(registryId: string, level: string, branch: string | null = null): Promise<Result<ReleasePreview>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.release(registryId, level, true, branch) };
  } catch (e) {
    return failed(e);
  }
}

export async function runRelease(projectId: string, _appId: string, registryId: string, level: string, branch: string | null = null): Promise<Result<ReleasePreview>> {
  await requireOrg();
  try {
    const data = await api.apps.release(registryId, level, false, branch);
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function pushApp(projectId: string, appId: string, registryId: string, priv: boolean, sourceHostId: string | null): Promise<{ ok: true; url: string } | { ok: false; error: string }> {
  await requireOrg();
  try {
    if (sourceHostId) await v1.setAppHost(projectId, appId, sourceHostId);
    const r = await api.apps.push(registryId, priv);
    await v1.syncImports(projectId, appId).catch(() => null);
    refresh(projectId);
    return { ok: true, url: r.url };
  } catch (e) {
    return failed(e);
  }
}

export async function startBranch(projectId: string, _appId: string, registryId: string, input: { kind: string; code: string; slug: string; push: boolean }): Promise<Result<{ branch: string; base: string; pushed: boolean }>> {
  await requireOrg();
  try {
    const data = await api.apps.startBranch(registryId, { ...input, slug: input.slug || null });
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function checkoutBranch(projectId: string, registryId: string, branch: string): Promise<Result<{ branch: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.checkout(registryId, branch)) as { branch: string };
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function proposePullRequest(_projectId: string, registryId: string): Promise<Result<{ head: string; base: string; title: string; body: string; commits: string[] }>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.proposePullRequest(registryId) };
  } catch (e) {
    return failed(e);
  }
}

export async function openPullRequest(projectId: string, _appId: string, registryId: string, input: { base: string; title: string; body: string; draft: boolean }): Promise<Result<{ number: number; url: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.openPullRequest(registryId, input);
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function saveManifest(projectId: string, registryId: string, content: string): Promise<Result<{ content: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.writeManifest(registryId, content);
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function setCloudTarget(projectId: string, registryId: string, target: string, source: string | null = null): Promise<Result<{ target: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.setCloud(registryId, target, source)) as { target: string };
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function addService(projectId: string, registryId: string, name: string, provider: string | null, source: string | null = null): Promise<Result<{ name: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.addService(registryId, name, provider, source)) as { name: string };
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export type CommitInput = { message: string; push: boolean; branch: { kind: string; code: string; slug: string } | null; pullRequest: boolean };

export async function commitChanges(projectId: string, _appId: string, registryId: string, input: CommitInput): Promise<Result<{ sha: string; branch: string; pushed: boolean; pull_request?: { number: number; url: string } | null }>> {
  await requireOrg();
  try {
    const data = await api.apps.commit(registryId, {
      message: input.message,
      push: input.push,
      branch: input.branch ? { kind: input.branch.kind, code: input.branch.code, slug: input.branch.slug || null } : null,
      pull_request: input.pullRequest,
    });
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function discardChanges(projectId: string, registryId: string): Promise<Result<{ files: string[]; clean: boolean }>> {
  await requireOrg();
  try {
    const data = await api.apps.discard(registryId);
    refresh(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}
