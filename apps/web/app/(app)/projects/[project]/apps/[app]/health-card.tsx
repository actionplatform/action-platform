import { Check, CircleDashed, GitCommitHorizontal, ShieldCheck, TriangleAlert, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { AppView } from "./model";

type Status = "ready" | "checking" | "warning" | "blocked" | "error";

function statusOf(view: AppView): Status {
  if (view.workingTree === "unknown") return "error";
  if (!view.health.ok) return "blocked";
  if (view.workingTree === "dirty") return "warning";
  return "ready";
}

const LABEL: Record<Status, string> = { ready: "Ready", checking: "Checking", warning: "Attention", blocked: "Blocked", error: "Unavailable" };

function Check_({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5">
      <Icon className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="truncate text-sm">{value}</div>
      </div>
    </div>
  );
}

export function HealthCard({ view }: { view: AppView }) {
  const status = statusOf(view);
  const tone = status === "ready" ? "ok" : status === "blocked" || status === "warning" ? "inverse" : "neutral";
  const Icon = status === "ready" ? Check : status === "blocked" || status === "warning" ? TriangleAlert : CircleDashed;
  return (
    <Panel>
      <PanelHeader title="Repository health" aside={<Badge tone={tone} className="gap-1"><Icon className="size-3" strokeWidth={2.5} />{LABEL[status]}</Badge>} />
      <div className="grid grid-cols-1 divide-y divide-border-subtle sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <Check_ icon={CircleDashed} label="Working tree" value={view.workingTree === "clean" ? "Clean" : view.workingTree === "dirty" ? "Uncommitted changes" : "Unknown"} />
        <Check_ icon={GitCommitHorizontal} label="Commits checked" value={String(view.health.checked_commits)} />
        <Check_ icon={ShieldCheck} label="Branch policy" value={view.health.ok ? "Valid" : `${view.health.problems.length} ${view.health.problems.length === 1 ? "problem" : "problems"}`} />
      </div>
      {view.health.problems.length > 0 && (
        <ul className="space-y-1 border-t border-border px-4 py-3 text-sm">
          {view.health.problems.map((p) => <li key={p} className="flex gap-2"><TriangleAlert className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} />{p}</li>)}
        </ul>
      )}
      <div className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">Last check completed on <span className="font-mono">{view.branch || "—"}</span></div>
    </Panel>
  );
}
