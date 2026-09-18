"use server";

import { failed, type Result } from "@/lib/result";
import type { ReadinessRow } from "@/lib/releases";
import { refreshProject } from "@/lib/revalidate";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function checkReadiness(projectId: string, appId: string, tag: string, stage: string | null = null): Promise<Result<{ jobs: string[]; readiness: ReadinessRow[] }>> {
  await requireOrg();
  try {
    const data = await v1.checkReadiness(projectId, appId, tag, stage);
    refreshProject(projectId);
    return { ok: true, data: { jobs: data.jobs, readiness: data.readiness } };
  } catch (e) {
    return failed(e);
  }
}

export async function readiness(projectId: string, appId: string, tag: string): Promise<Result<ReadinessRow[]>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.readiness(projectId, appId, tag) };
  } catch (e) {
    return failed(e);
  }
}
