"use client";

import { ExternalLink, Workflow } from "lucide-react";
import { useMemo, useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { CI_LABELS, type CiRun, duration } from "@/lib/ci-kinds";
import { relativeTime } from "@/lib/time";
import { RunIcon } from "./run-badge";

export function RunsTable({ runs, source, action }: { runs: CiRun[]; source: string; action?: React.ReactNode }) {
  const [branch, setBranch] = useState("");
  const branches = useMemo(() => Array.from(new Set(runs.map((r) => r.branch).filter((b): b is string => !!b))).sort(), [runs]);
  const shown = branch ? runs.filter((r) => r.branch === branch) : runs;

  return (
    <Panel>
      <PanelHeader
        title="Runs"
        aside={
          <div className="flex items-center gap-3">
            {runs.length > 0 && <span className="hidden text-[13px] text-secondary sm:block">{runs.length} synced · {CI_LABELS[source] ?? source}</span>}
            {branches.length > 1 && <Select size="sm" mono value={branch} onChange={setBranch} placeholder="All branches" aria-label="Filter by branch" options={[{ value: "", label: "All branches" }, ...branches.map((b) => ({ value: b, label: b }))]} className="w-44" />}
            {action}
          </div>
        }
      />
      {shown.length === 0 ? (
        <div className="flex flex-col items-center px-4 py-10 text-center">
          <Workflow className="size-5 text-secondary" strokeWidth={1.5} />
          <div className="mt-3 text-sm font-medium">{runs.length === 0 ? "No runs yet" : "No runs on this branch"}</div>
          <div className="text-[13px] text-secondary">{runs.length === 0 ? "Sync to import the latest runs from the CI." : "Pick another branch."}</div>
        </div>
      ) : (
        <ul className="divide-y divide-border-subtle border-t border-border-subtle">
          {shown.map((r) => (
            <li key={r.id} className="flex items-start gap-3 px-4 py-3">
              <span className="mt-0.5"><RunIcon status={r.status} /></span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {r.url ? (
                    <a href={r.url} target="_blank" rel="noopener noreferrer" className="truncate text-sm font-medium hover:underline underline-offset-4">{r.name ?? `#${r.number}`}</a>
                  ) : (
                    <span className="truncate text-sm font-medium">{r.name ?? `#${r.number}`}</span>
                  )}
                  {r.name && r.name !== `#${r.number}` && <span className="font-mono text-xs text-muted-foreground">#{r.number}</span>}
                  {r.branch && <span className="font-mono text-xs text-secondary">{r.branch}</span>}
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-secondary">
                  {r.sha && <span className="font-mono">{r.sha.slice(0, 7)}</span>}
                  {r.trigger && <><span aria-hidden>·</span><span className="truncate">{r.trigger}</span></>}
                  {r.startedAt && <><span aria-hidden>·</span><span>{relativeTime(r.startedAt)}</span></>}
                  <span aria-hidden>·</span>
                  <span>{duration(r.durationMs)}</span>
                </div>
              </div>
              {r.url && <a href={r.url} target="_blank" rel="noopener noreferrer" aria-label={`Open run ${r.number}`} className="text-secondary hover:text-foreground"><ExternalLink className="size-4" strokeWidth={1.75} /></a>}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
