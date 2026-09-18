"use client";

import { ExternalLink, RefreshCw, Workflow } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { DataList } from "@/components/ui/data-list";
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
      const r = await call(() => syncCi(projectId, appId), (e) => ({ ok: false as const, error: e }), "Reload the page to see the current state.");
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
      <DataList
        title="CI runs"
        rows={state.runs}
        rowKey={(r) => r.id}
        noun={["run", "runs"]}
        meta={connected ? <>{CI_LABELS[state.link.kind] ?? state.link.kind}{state.link.job && <span className="font-mono"> · {state.link.job}</span>}</> : undefined}
        action={canSync && connected ? <Button size="sm" variant="outline" onClick={sync} disabled={pending}><RefreshCw className={`size-3.5 ${status === "syncing" ? "animate-spin" : ""}`} strokeWidth={2} /> {status === "syncing" ? "Syncing…" : status === "done" ? "Synced" : "Sync"}</Button> : undefined}
        newHref={connectHref}
        newLabel={connected ? "Change CI" : "Connect CI"}
        empty={{ icon: Workflow, title: connected ? "No runs yet" : "No CI connected", text: connected ? "Sync to import the latest runs from the CI." : "Connect a runner — a CI server of the organization, or the one in the source host — to read its runs here." }}
        minWidth="720px"
        columns={[
          { key: "status", label: "Status", render: (r) => <span className="flex items-center gap-2"><RunIcon status={r.status} /><RunBadge status={r.status} /></span> },
          { key: "run", label: "Run", className: "max-w-0 w-full", render: (r) => <span className="flex items-center gap-2 truncate">{r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="truncate font-medium hover:underline underline-offset-4">{name(r)}</a> : <span className="truncate font-medium">{name(r)}</span>}{r.name && r.name !== `#${r.number}` && <span className="font-mono text-xs text-muted-foreground">#{r.number}</span>}</span> },
          { key: "branch", label: "Branch", render: (r) => <span className="font-mono text-xs text-secondary">{r.branch ?? "—"}</span> },
          { key: "sha", label: "Commit", render: (r) => r.sha ? <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha.slice(0, 7)}</span> : <span className="text-muted-foreground">—</span> },
          { key: "trigger", label: "Trigger", className: "max-w-[200px]", render: (r) => <span className="block truncate text-secondary" title={r.trigger ?? undefined}>{r.trigger ?? "—"}</span> },
          { key: "when", label: "Started", render: (r) => <span className="whitespace-nowrap text-secondary">{r.startedAt ? relativeTime(r.startedAt) : "—"}</span> },
          { key: "duration", label: "Duration", render: (r) => <span className="font-mono text-secondary">{duration(r.durationMs)}</span> },
          { key: "open", label: "", className: "text-right", render: (r) => r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" aria-label={`Open run ${r.number}`} className="inline-flex text-secondary hover:text-foreground"><ExternalLink className="size-4" strokeWidth={1.75} /></a> : null },
        ]}
        card={(r) => (
          <>
            <div className="flex flex-wrap items-center gap-2"><RunIcon status={r.status} />{r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline underline-offset-4">{name(r)}</a> : <span className="font-medium">{name(r)}</span>}<RunBadge status={r.status} />{r.branch && <span className="font-mono text-xs text-secondary">{r.branch}</span>}</div>
            <div className="mt-1 flex flex-wrap gap-x-2 text-xs text-secondary">{r.sha && <span className="font-mono">{r.sha.slice(0, 7)}</span>}{r.trigger && <><span aria-hidden>·</span><span className="truncate">{r.trigger}</span></>}{r.startedAt && <><span aria-hidden>·</span><span>{relativeTime(r.startedAt)}</span></>}<span aria-hidden>·</span><span>{duration(r.durationMs)}</span></div>
          </>
        )}
      />
    </div>
  );
}
