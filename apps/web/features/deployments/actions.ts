"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function startDeploy(registryId: string, stage: string, dryRun: boolean, version: string): Promise<Result<{ job: string }>> {
  await requireOrg();
  if (!version) return { ok: false, error: "A deploy ships a release: pick one." };
  try {
    const data = await api.apps.deployAsync(registryId, stage, dryRun, version);
    return { ok: true, data: { job: data.job } };
  } catch (e) {
    return failed(e);
  }
}


export async function deployJob(projectId: string, id: string): Promise<Result<{ status: string; error: string | null; results: DeployResult[] }>> {
  await requireOrg();
  try {
    const job = await v1.job(id);
    if (job.status === "done") refreshProject(projectId);
    const results = Array.isArray(job.result) ? (job.result as DeployResult[]) : [];
    return { ok: true, data: { status: job.status, error: job.error ?? null, results } };
  } catch (e) {
    return failed(e);
  }
}
