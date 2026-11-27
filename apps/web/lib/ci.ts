import { v1 } from "./v1";
import { type CiHost, type CiHostActivity, type CiState, type PipelineRunDetail, type Pipelines, ciActivity, ciHost, type CiDeployRun, deployRuns, ciState, pipelineRunDetail, pipelines } from "./ci-kinds";

export * from "./ci-kinds";

export async function ciHostsOf(): Promise<CiHost[]> {
  return (await v1.ciHosts()).map(ciHost);
}

export async function ciOf(projectId: string, appId: string, page = 1, per = 10): Promise<CiState> {
  return ciState(await v1.ci(projectId, appId, page, per));
}

export async function pipelinesOf(projectId: string, appId: string, job: string | null, status: string | null): Promise<Pipelines> {
  return pipelines(await v1.pipelines(projectId, appId, job, status));
}

export async function pipelineRunOf(projectId: string, appId: string, job: string, number: number): Promise<PipelineRunDetail> {
  return pipelineRunDetail(await v1.pipelineRun(projectId, appId, job, number));
}

export async function ciActivityOf(): Promise<CiHostActivity[]> {
  return ciActivity(await v1.ciActivity());
}

export async function deployRunsOf(projectId: string, appId: string, q: { stage: string | null; version: string; since: string | null; until: string | null; urls: string[] }): Promise<CiDeployRun[]> {
  return deployRuns(await v1.deployRuns(projectId, appId, q));
}
