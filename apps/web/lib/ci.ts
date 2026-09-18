import { v1 } from "./v1";
import { type CiHost, type CiState, ciHost, ciState } from "./ci-kinds";

export * from "./ci-kinds";

export async function ciHostsOf(): Promise<CiHost[]> {
  return (await v1.ciHosts()).map(ciHost);
}

export async function ciOf(projectId: string, appId: string): Promise<CiState> {
  return ciState(await v1.ci(projectId, appId));
}
