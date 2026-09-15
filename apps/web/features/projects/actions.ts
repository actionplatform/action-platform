"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

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


export async function removeApp(projectId: string, appId: string, repository = false): Promise<{ ok: true } | { ok: false; error: string }> {
  await requireOrg();
  try {
    await v1.deleteApp(projectId, appId, repository);
  } catch (e) {
    return failed(e);
  }
  revalidatePath(`/projects/${projectId}`);
  return { ok: true };
}


export async function syncApp(projectId: string, appId: string, registryId: string): Promise<{ ok: true } | { ok: false; error: string }> {
  await requireOrg();
  try {
    await api.apps.sync(registryId);
    await v1.syncImports(projectId, appId).catch(() => null);
    refreshProject(projectId);
    return { ok: true };
  } catch (e) {
    return failed(e, "sync failed");
  }
}

