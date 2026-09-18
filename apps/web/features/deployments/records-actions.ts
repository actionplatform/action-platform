"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { type Deployment, type DeploymentsState, deployment, deploymentsState } from "@/lib/deployments-kinds";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function syncDeployments(projectId: string, appId: string): Promise<Result<DeploymentsState>> {
  await requireOrg();
  try {
    const data = deploymentsState(await v1.syncDeployments(projectId, appId));
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function recordDeployment(projectId: string, appId: string, body: { target: string; version: string; stage: string | null; url: string | null; ok: boolean }): Promise<Result<Deployment>> {
  await requireOrg();
  try {
    const row = deployment(await v1.recordDeployment(projectId, appId, { target: body.target, version: body.version, stage: body.stage, url: body.url, ok: body.ok }));
    refreshProject(projectId);
    return { ok: true, data: row };
  } catch (e) {
    return failed(e);
  }
}
