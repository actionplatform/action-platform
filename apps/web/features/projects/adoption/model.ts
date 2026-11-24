import type { Schemas } from "@/lib/api";

export type AdoptionRow = Schemas["AdoptionRow"];

export type InstallPlan = {
  type: string;
  language: string;
  ci: string;
  detected_ci: string[];
  created: string[];
  kept: string[];
  warnings: string[];
  version: string;
  version_source: string;
  base: string;
  branch: string;
};

export type InstallResult = {
  app_id: string;
  name: string;
  state: string;
  skipped: boolean;
  reason: string | null;
  pull_request: { number: number; url: string } | null;
  plan: InstallPlan | null;
};

export type InstallRun = { dry_run: boolean; branch: string; apps: InstallResult[]; opened: number; skipped: number; failed: number };

export type Tone = "neutral" | "ok" | "warning" | "danger" | "success";

export function stateLabel(row: { state: string; reason?: string | null; pull_request?: { number: number } | null }): { label: string; tone: Tone } {
  switch (row.state) {
    case "installed":
      return { label: "installed", tone: "success" };
    case "pr_open":
      return { label: row.pull_request ? `install PR #${row.pull_request.number} open` : "install PR open", tone: "ok" };
    case "missing":
      return { label: "no platform.toml", tone: "warning" };
    case "failed":
      return { label: row.reason ? `failed: ${row.reason}` : "failed", tone: "danger" };
    default:
      return { label: "not checked", tone: "neutral" };
  }
}

export function selectable(row: AdoptionRow): boolean {
  return row.state !== "installed" && row.state !== "pr_open";
}

export function toOpen(run: InstallRun | null): InstallResult[] {
  return (run?.apps ?? []).filter((a) => a.state === "missing" && a.plan !== null);
}
