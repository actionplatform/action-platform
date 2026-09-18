import { Cloud, GitMerge, Tag, Workflow } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Timeline } from "@/lib/insights";
import { relativeTime } from "@/lib/time";

const TONE: Record<string, "success" | "danger" | "neutral" | "warning"> = { verified: "success", success: "success", failure: "danger", running: "warning", queued: "neutral", aborted: "neutral", unstable: "warning" };

function Step({ icon: Icon, title, count, children }: { icon: typeof Tag; title: string; count: number; children: ReactNode }) {
  return (
    <li className="relative pl-8">
      <span className="absolute left-0 top-0 flex size-6 items-center justify-center rounded-full border border-border bg-surface"><Icon className="size-3.5 text-secondary" strokeWidth={1.75} /></span>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold">{title} <Badge className="h-5 px-2 text-[11px]">{count}</Badge></div>
      {children}
    </li>
  );
}

const Row = ({ children }: { children: ReactNode }) => <li className="flex items-center gap-3 px-4 text-sm" style={{ height: 44 }}>{children}</li>;
const List = ({ children }: { children: ReactNode }) => <ul className="divide-y divide-border-subtle rounded-lg border border-border bg-surface">{children}</ul>;
const Note = ({ children }: { children: ReactNode }) => <div className="text-[13px] text-secondary">{children}</div>;

export function TimelineView({ data, repositoryUrl }: { data: Timeline; repositoryUrl: string | null }) {
  const r = data.release;
  return (
    <Panel>
      <PanelHeader
        title={<><Tag className="size-4 text-secondary" strokeWidth={1.75} /> {r.tag}</>}
        description={<>{r.name ?? "Release"}{r.author && <> · {r.author}</>}{r.published_at && <> · {relativeTime(r.published_at)}</>}{data.previous && <> · since <span className="font-mono">{data.previous.tag}</span></>}</>}
        aside={<div className="flex items-center gap-2">{r.prerelease && <Badge>Pre-release</Badge>}<Badge className="font-mono">{r.source}</Badge>{r.url && <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-[13px] text-secondary hover:text-foreground">Open on the host</a>}</div>}
      />
      <ol className="relative space-y-6 p-4 pl-6">
        <Step icon={GitMerge} title="Pull requests merged" count={data.pull_requests.length}>
          {data.pull_requests.length === 0 ? <Note>None between {data.previous?.tag ?? "the start"} and {r.tag}.</Note> : (
            <List>{data.pull_requests.map((p) => <Row key={p.id}><a href={p.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 truncate font-medium hover:underline underline-offset-4">#{p.number} {p.title}</a><span className="shrink-0 font-mono text-xs text-secondary">{p.head} → {p.base}</span><span className="shrink-0 text-xs text-secondary">{p.author ?? ""}</span></Row>)}</List>
          )}
        </Step>
        <Step icon={Tag} title="Release" count={1}>
          <List>
            <Row><span className="font-mono font-medium">{r.version}</span><span className="font-mono text-xs text-secondary">{r.tag}</span>{r.sha && <span className="inline-flex h-6 items-center rounded border border-border bg-background px-1.5 font-mono text-xs">{r.sha.slice(0, 7)}</span>}<span className="ml-auto text-xs text-secondary">{r.published_at ? relativeTime(r.published_at) : ""}</span></Row>
          </List>
          {r.body && <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{r.body}</pre>}
        </Step>
        <Step icon={Workflow} title="CI runs on the tag" count={data.ci_runs.length}>
          {data.ci_runs.length === 0 ? <Note>No run on {r.tag} imported yet.</Note> : (
            <List>{data.ci_runs.map((c) => <Row key={c.id}><Badge tone={TONE[c.status] ?? "neutral"} className="h-5 px-2 text-[11px]">{c.status}</Badge>{c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 truncate font-medium hover:underline underline-offset-4">{c.name ?? `#${c.number}`}</a> : <span className="min-w-0 flex-1 truncate font-medium">{c.name ?? `#${c.number}`}</span>}<span className="shrink-0 font-mono text-xs text-secondary">{c.source}</span><span className="shrink-0 text-xs text-secondary">{c.started_at ? relativeTime(c.started_at) : ""}</span></Row>)}</List>
          )}
        </Step>
        <Step icon={Cloud} title="Deployments" count={data.deployments.length}>
          {data.deployments.length === 0 ? <Note>{r.version} has not reached a target yet.</Note> : (
            <List>{data.deployments.map((d) => <Row key={d.id}><Badge tone={TONE[d.status] ?? "neutral"} className="h-5 px-2 text-[11px]">{d.status}</Badge><span className="font-medium">{d.target}</span>{d.stage && <span className="font-mono text-xs text-secondary">{d.stage}</span>}<span className="text-xs text-secondary">{d.executor}</span>{d.url && <a href={d.url} target="_blank" rel="noopener noreferrer" className="min-w-0 truncate text-xs text-secondary hover:text-foreground">{d.url}</a>}<span className="ml-auto shrink-0 text-xs text-secondary">{(d.finished_at ?? d.started_at) ? relativeTime((d.finished_at ?? d.started_at)!) : ""}</span></Row>)}</List>
          )}
        </Step>
      </ol>
      {repositoryUrl && <div className="border-t border-border-subtle px-4 py-2 text-xs"><a href={`${repositoryUrl}/releases/tag/${r.tag}`} target="_blank" rel="noopener noreferrer" className="text-secondary hover:text-foreground">View the tag on the host</a></div>}
    </Panel>
  );
}
