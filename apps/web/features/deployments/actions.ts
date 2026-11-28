"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, type DeployResult, type Rollout } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";
import type { Control, DeploymentStep, StrategyDef, StrategySupport, JsonSchema } from "./strategies";

export async function startDeploy(projectId: string, registryId: string, stage: string, dryRun: boolean, version: string, force = false, rollout: Rollout = {}): Promise<Result<{ job: string } | { dryRun: true; rows: DeployResult[] }>> {
  await requireOrg();
  if (!version) return { ok: false, error: "A deploy ships a release: pick one." };
  try {
    if (dryRun) {
      const rows = (await api.apps.preflight(projectId, registryId, stage, version, force)) as DeployResult[];
      const refused = rows.find((r) => !r.ok);
      if (refused) return { ok: false, error: refused.error ?? `${refused.target} failed preflight` };
      return { ok: true, data: { dryRun: true, rows } };
    }
    const data = await api.apps.deployAsync(projectId, registryId, stage, version, force, rollout);
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

export async function strategyCatalog(): Promise<Result<{ strategies: StrategyDef[]; safety: JsonSchema }>> {
  await requireOrg();
  try {
    const found = await v1.deployStrategies();
    return { ok: true, data: { strategies: found.strategies as StrategyDef[], safety: found.safety_schema as JsonSchema } };
  } catch (e) {
    return failed(e);
  }
}

export async function scopeStrategies(projectId: string, appId: string, scope: string): Promise<Result<StrategySupport[]>> {
  await requireOrg();
  try {
    return { ok: true, data: (await v1.scopeStrategies(projectId, appId, scope)) as StrategySupport[] };
  } catch (e) {
    return failed(e);
  }
}

export async function deploymentSteps(projectId: string, appId: string, deploymentId: string): Promise<Result<DeploymentStep[]>> {
  await requireOrg();
  try {
    return { ok: true, data: (await v1.deploymentSteps(projectId, appId, deploymentId)) as DeploymentStep[] };
  } catch (e) {
    return failed(e);
  }
}

export async function controlDeployment(projectId: string, appId: string, deploymentId: string, action: Control): Promise<Result<{ steps: DeploymentStep[]; status: string }>> {
  await requireOrg();
  try {
    const found = await v1.deploymentControl(projectId, appId, deploymentId, action);
    refreshProject(projectId);
    return { ok: true, data: { steps: found.steps as DeploymentStep[], status: found.deployment.status } };
  } catch (e) {
    return failed(e);
  }
}
