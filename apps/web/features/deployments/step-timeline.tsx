"use client";

import { Check, ChevronRight, Circle, CircleDashed, Loader2, Pause, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { when } from "./job-state";
import { type DeploymentStep, type StepTone, stepDetail, stepLabel, stepTone, stepWeight } from "./strategies";

const ICONS: Record<StepTone, { icon: typeof Check; className: string; spin?: boolean }> = {
  done: { icon: Check, className: "border-status-ok/40 bg-status-ok/10 text-status-ok" },
  active: { icon: Loader2, className: "border-status-warn/40 bg-status-warn/10 text-status-warn", spin: true },
  failed: { icon: X, className: "border-status-bad/40 bg-status-bad/10 text-status-bad" },
  waiting: { icon: Pause, className: "border-status-run/40 bg-status-run/10 text-status-run" },
  skipped: { icon: Circle, className: "border-border text-muted-foreground" },
};

function timing(step: DeploymentStep): string | null {
  if (!step.started_at) return null;
  const from = new Date(step.started_at).getTime();
  const to = step.finished_at ? new Date(step.finished_at).getTime() : null;
  if (to === null || Number.isNaN(from) || Number.isNaN(to)) return when(step.started_at);
  const s = Math.max(0, Math.round((to - from) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

function Row({ step }: { step: DeploymentStep }) {
  const [open, setOpen] = useState(false);
  const tone = stepTone(step.status);
  const idle = step.status === "pending" || step.status === "queued";
  const { icon: Icon, className, spin } = idle ? { icon: CircleDashed, className: "border-border text-muted-foreground", spin: false } : ICONS[tone];
  const weight = stepWeight(step);
  const note = stepDetail(step);
  const time = timing(step);
  const expandable = !!step.detail || (!!step.data && Object.keys(step.data).length > 0);

  return (
    <li className="relative pl-9" data-status={step.status}>
      <span aria-hidden className="absolute bottom-0 left-[11px] top-7 w-px bg-border-subtle" />
      <span aria-hidden className={cn("absolute left-0 top-1.5 inline-flex size-[23px] items-center justify-center rounded-full border", className)}>
        <Icon className={cn("size-3", spin && "animate-spin")} strokeWidth={2} />
      </span>
      <button type="button" aria-expanded={expandable ? open : undefined} disabled={!expandable} onClick={() => setOpen((o) => !o)} className="flex w-full min-w-0 items-center gap-2 rounded-md px-2 py-2 text-left text-sm enabled:hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
        <span className="font-medium">{stepLabel(step.kind)}</span>
        {weight !== null && <span className="rounded-full border border-border px-1.5 font-mono text-xs text-secondary">{weight}%</span>}
        {note && <span className="min-w-0 truncate text-[13px] text-secondary">{note}</span>}
        <span className="ml-auto flex shrink-0 items-center gap-2 text-xs text-secondary" suppressHydrationWarning>
          {time}
          {expandable && <ChevronRight className={cn("size-3.5 transition-transform", open && "rotate-90")} strokeWidth={1.75} />}
        </span>
      </button>
      {open && expandable && (
        <div className="mb-2 ml-2 space-y-2 rounded-md border border-border bg-background p-3 text-[13px]">
          {step.detail && <p className="whitespace-pre-wrap break-words font-mono text-xs leading-5 text-secondary">{step.detail}</p>}
          {step.data && Object.keys(step.data).length > 0 && <pre className="overflow-auto font-mono text-xs leading-5 text-secondary">{JSON.stringify(step.data, null, 2)}</pre>}
        </div>
      )}
    </li>
  );
}

export function StepTimeline({ steps }: { steps: DeploymentStep[] }) {
  if (steps.length === 0) return <p className="text-[13px] text-secondary">No steps recorded yet.</p>;
  return (
    <ol aria-label="Deployment steps" className="space-y-0.5">
      {steps.map((s) => <Row key={s.index} step={s} />)}
    </ol>
  );
}
