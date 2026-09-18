import type { Schemas } from "./api";
import { v1 } from "./v1";

export type Dashboard = Schemas["Dashboard"];
export type DashboardEvent = Schemas["Event"];
export type Timeline = Schemas["Timeline"];

export async function dashboardOf(): Promise<Dashboard> {
  return v1.dashboard();
}

export async function timelineOf(projectId: string, appId: string, tag: string): Promise<Timeline> {
  return v1.timeline(projectId, appId, tag);
}
