"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function nextVersion(registryId: string, level: string, branch: string | null = null, component: string | null = null): Promise<Result<{ current: string; next: string; branch: string; prerelease: boolean }>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.nextVersion(registryId, level, branch, component) };
  } catch (e) {
    return failed(e);
  }
}


export async function previewRelease(registryId: string, level: string, branch: string | null = null, component: string | null = null): Promise<Result<ReleasePreview>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.release(registryId, level, true, branch, { component }) };
  } catch (e) {
    return failed(e);
  }
}


export type ReleaseExtra = { name?: string | null; notes?: string | null; latest?: boolean; component?: string | null };


export async function runRelease(projectId: string, _appId: string, registryId: string, level: string, branch: string | null = null, extra: ReleaseExtra = {}): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.releaseAsync(registryId, level, branch, extra);
    return { ok: true, data: { job: data.job } };
  } catch (e) {
    return failed(e);
  }
}


export async function releaseJob(projectId: string, id: string): Promise<Result<{ status: string; error: string | null; result: ReleasePreview | null }>> {
  await requireOrg();
  try {
    const job = await v1.job(id);
    if (job.status === "done") refreshProject(projectId);
    const result = job.result && typeof job.result === "object" && "next" in (job.result as object) ? (job.result as ReleasePreview) : null;
    return { ok: true, data: { status: job.status, error: job.error ?? null, result } };
  } catch (e) {
    return failed(e);
  }
}

