"use client";

import { ExternalLink, RefreshCw, Workflow } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import { CI_LABELS, type CiRun, type CiState, duration } from "@/lib/ci-kinds";
import { call } from "@/lib/call";
import { relativeTime } from "@/lib/time";
import { syncCi } from "./actions";
import { RunBadge, RunIcon } from "./run-badge";

type Props = { projectId: string; appId: string; state: CiState; connectHref: string | null; canSync: boolean };

export function RunsTable({ projectId, appId, state: initial, connectHref, canSync }: Props) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [error, setError] = useState<string | null>(initial.error);
  const [status, setStatus] = useState<"idle" | "syncing" | "done">("idle");
  const [pending, start] = useTransition();
  const connected = state.link.kind !== "none";

  const sync = () =>
    start(async () => {
      setStatus("syncing");
      const r = await call(() => syncCi(projectId, appId, state.page, state.per), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
      if (!r.ok) { setError(r.error); setStatus("idle"); return; }
      setState(r.data);
      setError(r.data.error);
      setStatus("done");
      setTimeout(() => setStatus("idle"), 2500);
      router.refresh();
    });

  const name = (r: CiRun) => r.name && r.name !== `#${r.number}` ? r.name : `#${r.number}`;

  return (
    <div className="space-y-3">
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      <DataTable
        title="CI runs"
        rows={state.runs}
        paging={{ total: state.total, page: state.page, per: state.per }}
        rowKey={(r) => r.id}
        noun={["run", "runs"]}
        meta={connected ? <>{CI_LABELS[state.link.kind] ?? state.link.kind}{state.link.job && <span className="font-mono"> · {state.link.job}</span>}</> : undefined}
        action={canSync && connected ? <Button size="sm" variant="outline" onClick={sync} disabled={pending}><RefreshCw className={`size-3.5 ${status === "syncing" ? "animate-spin" : ""}`} strokeWidth={2} /> {status === "syncing" ? "Syncing…" : status === "done" ? "Synced" : "Sync"}</Button> : undefined}
        newHref={connectHref}
        newLabel={connected ? "Change CI" : "Connect CI"}
        empty={{ icon: Workflow, title: connected ? "No runs yet" : "No CI connected", text: connected ? "Sync to import the latest runs from the CI." : "Connect a runner — a CI server of the organization, or the one in the source host — to read its runs here." }}
        minWidth={880}
        columns={[
          { key: "status", label: "Status", width: 10, render: (r) => <Inline><RunIcon status={r.status} /><RunBadge status={r.status} /></Inline> },
          { key: "run", label: "Run", width: 47, render: (r) => <Inline>{r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="min-w-0 truncate font-medium hover:underline underline-offset-4" title={name(r)}>{name(r)}</a> : <span className="min-w-0 truncate font-medium" title={name(r)}>{name(r)}</span>}{r.name && r.name !== `#${r.number}` && <span className="shrink-0 font-mono text-xs text-muted-foreground">#{r.number}</span>}</Inline> },
          { key: "branch", label: "Branch", width: 8, hide: "md", render: (r) => <Cell mono muted title={r.branch ?? undefined}>{r.branch ?? "—"}</Cell> },
          { key: "sha", label: "Commit", width: 7, hide: "md", render: (r) => r.sha ? <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha.slice(0, 7)}</span> : <Cell muted>—</Cell> },
          { key: "trigger", label: "Trigger", width: 10, hide: "md", render: (r) => <Cell muted title={r.trigger ?? undefined}>{r.trigger ?? "—"}</Cell> },
          { key: "when", label: "Started", width: 10, hide: "sm", render: (r) => <Cell muted>{r.startedAt ? relativeTime(r.startedAt) : "—"}</Cell> },
          { key: "duration", label: "Duration", width: 5, hide: "sm", render: (r) => <Cell mono muted>{duration(r.durationMs)}</Cell> },
          { key: "open", label: "", width: 3, align: "right", render: (r) => r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" aria-label={`Open run ${r.number}`} className="inline-flex text-secondary hover:text-foreground"><ExternalLink className="size-4" strokeWidth={1.75} /></a> : null },
        ]}
      />
    </div>
  );
}
