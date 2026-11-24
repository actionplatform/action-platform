import type { AccessChange, AccessPlan } from "@/lib/v1";

export type PlanSummary = { total: number; planned: number; applied: number; refused: number; failed: number; add: number; change: number; remove: number };

export function summarizePlan(plan: Pick<AccessPlan, "changes">): PlanSummary {
  const out: PlanSummary = { total: 0, planned: 0, applied: 0, refused: 0, failed: 0, add: 0, change: 0, remove: 0 };
  for (const c of plan.changes ?? []) {
    out.total += 1;
    out[c.status] += 1;
    out[c.action] += 1;
  }
  return out;
}

export function summaryText(s: PlanSummary): string {
  if (s.total === 0) return "No changes";
  const parts = [s.add && `${s.add} to add`, s.change && `${s.change} to change`, s.remove && `${s.remove} to remove`, s.applied && `${s.applied} applied`, s.refused && `${s.refused} refused`, s.failed && `${s.failed} failed`];
  return parts.filter(Boolean).join(", ");
}

export function canApply(plan: Pick<AccessPlan, "dry_run" | "bootstrap" | "changes">): boolean {
  if (!plan.dry_run) return false;
  return plan.bootstrap || summarizePlan(plan).planned > 0;
}

export function groupDrift(drift: AccessChange[]): { service: string; changes: AccessChange[] }[] {
  const groups = new Map<string, AccessChange[]>();
  for (const c of drift) groups.set(c.service, [...(groups.get(c.service) ?? []), c]);
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([service, changes]) => ({ service, changes }));
}

export function needsConnection(error: string | null | undefined): boolean {
  return !!error && /\bconnect/i.test(error);
}

export function describeChange(c: AccessChange): string {
  const target = `${c.account} on ${c.resource}`;
  if (c.action === "add") return `Add ${target} at ${c.level}`;
  if (c.action === "remove") return `Remove ${target} (${c.level})`;
  return `Change ${target} from ${c.previous ?? "none"} to ${c.level}`;
}
