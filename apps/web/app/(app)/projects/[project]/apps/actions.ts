"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { appById, createApp, deleteApp, projectById, setAppHost } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { credentialsFor } from "@/lib/source-hosts";

async function owned(projectId: string) {
  const { org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  if (!project) throw new Error("project not found");
  return { org, project };
}

async function credsFor(orgId: string, projectId: string, appId: string) {
  const app = await appById(projectId, appId);
  if (!app?.sourceHostId) return null;
  return credentialsFor(orgId, app.sourceHostId);
}

export async function addApp(projectId: string, _prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  const url = String(formData.get("url") ?? "").trim();
  if (!url) return null;
  try {
    await owned(projectId);
    const entry = await api.apps.add(url);
    await createApp(projectId, entry.id, entry.name);
  } catch (e) {
    return { error: (e as Error).message };
  }
  revalidatePath(`/projects/${projectId}`);
  return null;
}

export async function removeApp(projectId: string, appId: string) {
  await owned(projectId);
  const app = await deleteApp(projectId, appId);
  if (app) await api.apps.remove(app.registryId).catch(() => {});
  revalidatePath(`/projects/${projectId}`);
}

export async function syncApp(projectId: string, registryId: string) {
  await owned(projectId);
  await api.apps.sync(registryId);
  revalidatePath(`/projects/${projectId}`, "layout");
}

export async function previewRelease(registryId: string, level: string) {
  await requireOrg();
  return api.apps.release(registryId, level, true);
}

export async function runRelease(projectId: string, appId: string, registryId: string, level: string) {
  const { org } = await owned(projectId);
  const result = await api.apps.release(registryId, level, false, await credsFor(org.id, projectId, appId));
  revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

export async function previewDeploy(registryId: string, stage: string | null) {
  await requireOrg();
  return api.apps.deploy(registryId, stage, true);
}

export async function runDeploy(projectId: string, registryId: string, stage: string | null) {
  await owned(projectId);
  const result = await api.apps.deploy(registryId, stage, false);
  revalidatePath(`/projects/${projectId}`, "layout");
  return result;
}

export async function pushApp(projectId: string, appId: string, registryId: string, priv: boolean, sourceHostId: string | null): Promise<{ ok: true; url: string } | { ok: false; error: string }> {
  const { org } = await owned(projectId);
  try {
    if (sourceHostId) await setAppHost(projectId, appId, sourceHostId);
    const creds = sourceHostId ? await credentialsFor(org.id, sourceHostId) : await credsFor(org.id, projectId, appId);
    if (!creds) return { ok: false, error: "pick a source host first (Settings → Source hosts)" };
    const r = await api.apps.push(registryId, priv, creds);
    revalidatePath(`/projects/${projectId}`, "layout");
    return { ok: true, url: r.url };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}
