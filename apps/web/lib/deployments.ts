import { v1 } from "./v1";
import { type DeploymentsState, deploymentsState } from "./deployments-kinds";

export * from "./deployments-kinds";

export async function deploymentsOf(projectId: string, appId: string): Promise<DeploymentsState> {
  return deploymentsState(await v1.deployments(projectId, appId));
}
