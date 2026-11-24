import { Badge } from "@/components/ui/badge";
import type { AccessPlan } from "@/lib/v1";
import { ChangeTable } from "./change-table";
import { summarizePlan, summaryText } from "./plan";

export function PlanView({ plan }: { plan: AccessPlan }) {
  const summary = summarizePlan(plan);
  return (
    <div className="rounded-lg border border-border">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2.5 text-sm">
        <Badge tone={plan.dry_run ? "warning" : "success"}>{plan.dry_run ? "Dry run" : "Applied"}</Badge>
        <span className="font-medium">{summaryText(summary)}</span>
        {summary.refused > 0 && <Badge tone="danger">{summary.refused} refused</Badge>}
      </div>
      {plan.note && <p className="border-b border-border px-4 py-2.5 text-[13px] text-secondary">{plan.note}</p>}
      {plan.errors && plan.errors.length > 0 && (
        <ul className="space-y-1 border-b border-status-bad/30 bg-status-bad/5 px-4 py-2.5 text-[13px] text-status-bad">
          {plan.errors.map((e) => <li key={e} className="whitespace-pre-wrap break-words">{e}</li>)}
        </ul>
      )}
      {plan.changes && plan.changes.length > 0 && <ChangeTable changes={plan.changes} />}
    </div>
  );
}
