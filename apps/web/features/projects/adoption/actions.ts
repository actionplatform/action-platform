"use server";

import { revalidatePath } from "next/cache";
import type { Schemas } from "@/lib/api";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import type { InstallRun } from "./model";

export async function startInstall(projectId: string, body: Schemas["ProjectInstallRequest"]): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.installApps(projectId, body) };
  } catch (e) {
    return failed(e);
  }
}

export async function installJob(projectId: string, id: string): Promise<Result<{ status: string; result: InstallRun | null; error: string | null }>> {
  await requireOrg();
  try {
    const job = await v1.job(id);
    if (job.status === "done") revalidatePath(`/projects/${projectId}/adoption`);
    return { ok: true, data: { status: job.status, result: (job.result as InstallRun | null) ?? null, error: job.error ?? null } };
  } catch (e) {
    return failed(e);
  }
}
