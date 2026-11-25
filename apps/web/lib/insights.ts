import type { Schemas } from "./api";
import { v1 } from "./v1";

export type Dashboard = Schemas["Dashboard"];
export type DashboardEvent = Schemas["Event"];
export type ActiveDeployment = Schemas["ActiveDeployment"];
export type Timeline = Schemas["Timeline"];

export async function dashboardOf(): Promise<Dashboard> {
  return v1.dashboard();
}

export const EVENT_KINDS = ["release", "deployment", "ci_run", "pull_request", "protection"] as const;
export type EventKind = (typeof EVENT_KINDS)[number];

export function eventKind(value: string | string[] | undefined): EventKind | null {
  const one = Array.isArray(value) ? value[0] : value;
  return (EVENT_KINDS as readonly string[]).includes(one ?? "") ? (one as EventKind) : null;
}

export async function appActivityOf(projectId: string, appId: string, kind: EventKind | null = null): Promise<DashboardEvent[]> {
  return (await v1.appActivity(projectId, appId, kind)).events;
}

export async function timelineOf(projectId: string, appId: string, tag: string): Promise<Timeline> {
  return v1.timeline(projectId, appId, tag);
}
