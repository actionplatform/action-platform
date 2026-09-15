"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function saveManifest(projectId: string, registryId: string, content: string): Promise<Result<{ content: string; mirrored?: boolean | null }>> {
  await requireOrg();
  try {
    const data = await api.apps.writeManifest(registryId, content);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function exportManifest(projectId: string, registryId: string): Promise<Result<{ content: string; mirrored?: boolean | null }>> {
  await requireOrg();
  try {
    const data = await api.apps.exportManifest(registryId);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function setCloudTarget(projectId: string, registryId: string, target: string, source: string | null = null): Promise<Result<{ target: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.setCloud(registryId, target, source)) as { target: string };
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function addService(projectId: string, registryId: string, name: string, provider: string | null, source: string | null = null): Promise<Result<{ name: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.addService(registryId, name, provider, source)) as { name: string };
    refreshProject(projectId);
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
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function discardChanges(projectId: string, registryId: string): Promise<Result<{ files: string[]; clean: boolean }>> {
  await requireOrg();
  try {
    const data = await api.apps.discard(registryId);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

