"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function nextVersion(registryId: string, level: string, branch: string | null = null): Promise<Result<{ current: string; next: string; branch: string; prerelease: boolean }>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.nextVersion(registryId, level, branch) };
  } catch (e) {
    return failed(e);
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


export type ReleaseExtra = { name?: string | null; notes?: string | null; latest?: boolean };


export async function runRelease(projectId: string, _appId: string, registryId: string, level: string, branch: string | null = null, extra: ReleaseExtra = {}): Promise<Result<ReleasePreview>> {
  await requireOrg();
  try {
    const data = await api.apps.release(registryId, level, false, branch, extra);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

