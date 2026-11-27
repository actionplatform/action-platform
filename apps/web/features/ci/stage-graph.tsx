"use client";

import { ChevronRight } from "lucide-react";
import { type CiRunStatus, type CiStage, duration } from "@/lib/ci-kinds";
import { cn } from "@/lib/utils";
import { RunIcon } from "./run-badge";
import { stageColumns } from "./stages";

type Props = { stages: CiStage[]; selected: string | null; onSelect: (id: string | null) => void };

const EDGE: Record<CiRunStatus, string> = {
  success: "border-status-ok/50",
  failure: "border-status-bad/60",
  unstable: "border-status-warn/60",
  aborted: "border-border",
  running: "border-status-run/60",
  queued: "border-border",
  unknown: "border-border",
};

function StageBox({ stage, selected, onSelect, nested }: { stage: CiStage; selected: boolean; onSelect: (id: string) => void; nested?: boolean }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(stage.id)}
      aria-pressed={selected}
      className={cn(
        "flex w-full min-w-0 items-center gap-2 rounded-md border bg-background px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground",
        EDGE[stage.status] ?? "border-border",
        selected && "bg-surface-selected ring-1 ring-foreground",
        nested && "py-1.5",
      )}
    >
      <RunIcon status={stage.status} />
      <span className="min-w-0 flex-1 truncate" title={stage.name}>{stage.name}</span>
      <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{duration(stage.durationMs)}</span>
    </button>
  );
}

export function StageGraph({ stages, selected, onSelect }: Props) {
  const columns = stageColumns(stages);
  if (columns.length === 0) return null;

  return (
    <div className="overflow-x-auto pb-1">
      <ol aria-label="Stages" className="flex min-w-max items-start gap-1">
        {columns.map((col, i) => (
          <li key={col.stage.id} className="flex items-start gap-1">
            <div className="w-52 space-y-1">
              <StageBox stage={col.stage} selected={selected === col.stage.id} onSelect={onSelect} />
              {col.branches.length > 0 && (
                <ul aria-label={`Parallel branches of ${col.stage.name}`} className="space-y-1 border-l border-border pl-2">
                  {col.branches.map((b) => (
                    <li key={b.stage.id} style={{ paddingLeft: `${(b.depth - 1) * 8}px` }}>
                      <StageBox stage={b.stage} selected={selected === b.stage.id} onSelect={onSelect} nested />
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {i < columns.length - 1 && <ChevronRight aria-hidden className="mt-2.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />}
          </li>
        ))}
      </ol>
    </div>
  );
}
