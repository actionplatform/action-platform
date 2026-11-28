import { v1 } from "@/lib/v1";
import type { RolloutView } from "./rollout-panel";
import type { Config, DeploymentStep, Safety } from "./strategies";

export type RunRollout = { strategy: string; status: string };

async function deploymentsOf(projectId: string, appId: string) {
  const found = await v1.deployments(projectId, appId).catch(() => null);
  return found && "deployments" in found ? found.deployments : [];
}

export async function rolloutsOf(projectId: string, appId: string, jobId: string): Promise<RolloutView[]> {
  const mine = (await deploymentsOf(projectId, appId)).filter((d) => d.job_id === jobId);
  const found = await Promise.all(
    mine.map(async (d) => {
      const steps = (await v1.deploymentSteps(projectId, appId, d.id).catch(() => [])) as DeploymentStep[];
      return { id: d.id, target: d.target, status: d.status, strategy: d.strategy, strategy_config: (d.strategy_config ?? null) as Config | null, safety: (d.safety ?? null) as Partial<Safety> | null, steps };
    }),
  );
  return found.filter((r) => r.steps.length > 0);
}

export async function runRolloutsOf(projectId: string, appId: string): Promise<Record<string, RunRollout>> {
  const out: Record<string, RunRollout> = {};
  for (const d of await deploymentsOf(projectId, appId)) {
    if (!d.job_id) continue;
    const known = out[d.job_id];
    if (!known || known.strategy === "recreate") out[d.job_id] = { strategy: d.strategy, status: d.status };
  }
  return out;
}
