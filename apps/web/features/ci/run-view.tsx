"use client";

import { Hourglass, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { type PipelineRunDetail, duration, logDownloadHref, runHref } from "@/lib/ci-kinds";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";
import { ArtifactsPanel } from "./artifacts-panel";
import { Console } from "./console";
import { RunBadge } from "./run-badge";
import { StageGraph } from "./stage-graph";
import { TestsPanel } from "./tests-panel";

const REFRESH_MS = 5000;

type Tab = "log" | "tests" | "artifacts" | "details";

export type RunTab = Tab;

type Props = { projectId: string; appId: string; base: string; repositoryUrl: string | null; detail: PipelineRunDetail; tab: Tab };

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-secondary">{label}</dt>
      <dd className="mt-0.5 truncate text-[13px]">{children}</dd>
    </div>
  );
}

export function RunView({ projectId, appId, base, repositoryUrl, detail, tab }: Props) {
  const router = useRouter();
  const { run } = detail;
  const live = run.status === "running" || run.status === "queued";
  const [node, setNode] = useState<string | null>(null);
  const stage = detail.stages?.find((s) => s.id === node) ?? null;

  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => router.refresh(), REFRESH_MS);
    return () => clearInterval(t);
  }, [live, router]);

  const tabs: { id: Tab; label: string; shown: boolean }[] = [
    { id: "log", label: "Log", shown: detail.supports.log },
    { id: "tests", label: "Tests", shown: detail.supports.tests },
    { id: "artifacts", label: "Artifacts", shown: detail.supports.artifacts },
    { id: "details", label: "Parameters and changes", shown: true },
  ];

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader
          title={<><RunBadge status={run.status} /><span className="font-mono">#{run.number}</span><span className="truncate font-normal text-secondary">{detail.job.label}{detail.job.name && <span className="font-mono"> · {detail.job.name}</span>}</span></>}
          aside={live ? <span className="inline-flex items-center gap-1.5 text-xs text-secondary"><RefreshCw className="size-3.5 animate-spin" strokeWidth={2} /> Live</span> : undefined}
        />
        <PanelBody>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
            <Fact label="Ref"><span className="font-mono">{run.branch ?? "—"}</span></Fact>
            <Fact label="Commit"><span className="font-mono">{run.sha ? run.sha.slice(0, 7) : "—"}</span></Fact>
            <Fact label="Started">{run.startedAt ? relativeTime(run.startedAt) : "—"}</Fact>
            <Fact label="Duration">{duration(run.durationMs)}</Fact>
            <Fact label="Started by">{detail.causes.length ? detail.causes.join(" · ") : run.trigger ?? "—"}</Fact>
          </dl>
          {detail.waiting && (
            <p className="mt-3 flex items-center gap-2 text-[13px] text-secondary"><Hourglass className="size-3.5" strokeWidth={2} /> Waiting: {detail.waiting}</p>
          )}
          {detail.pendingInputs && detail.pendingInputs.length > 0 && (
            <ul aria-label="Waiting for input" className="mt-3 space-y-1">
              {detail.pendingInputs.map((i) => (
                <li key={i.id} className="flex items-center gap-2 rounded-md border border-status-warn/40 bg-status-warn/10 px-3 py-2 text-[13px]"><Hourglass className="size-3.5 text-status-warn" strokeWidth={2} /> Waiting for input: {i.message || i.id}</li>
              ))}
            </ul>
          )}
        </PanelBody>
      </Panel>

      {detail.stages && detail.stages.length > 0 && (
        <Panel>
          <PanelHeader title="Stages" description={stage ? <>Log of <span className="font-medium text-foreground">{stage.name}</span> · <button type="button" className="underline underline-offset-4" onClick={() => setNode(null)}>whole console</button></> : "Select a stage to read its log."} />
          <PanelBody><StageGraph stages={detail.stages} selected={node} onSelect={(id) => { setNode(id === node ? null : id); }} /></PanelBody>
        </Panel>
      )}

      <nav aria-label="Run" className="border-b border-border">
        <ul role="tablist" className="flex gap-1">
          {tabs.filter((t) => t.shown).map((t) => (
            <li key={t.id} role="presentation">
              <Link href={runHref(base, run.job, run.number, t.id)} scroll={false} role="tab" aria-selected={t.id === tab} className={cn("-mb-px flex h-11 items-center border-b-2 px-3 text-sm", t.id === tab ? "border-foreground text-foreground" : "border-transparent text-secondary hover:text-foreground")}>{t.label}</Link>
            </li>
          ))}
        </ul>
      </nav>

      {tab === "log" && detail.supports.log && (
        <Console projectId={projectId} appId={appId} job={run.job} number={run.number} node={node} live={live} downloadHref={node ? null : logDownloadHref(projectId, appId, run.job, run.number)} />
      )}
      {tab === "tests" && detail.supports.tests && <TestsPanel projectId={projectId} appId={appId} job={run.job} number={run.number} />}
      {tab === "artifacts" && detail.supports.artifacts && <ArtifactsPanel projectId={projectId} appId={appId} job={run.job} number={run.number} />}
      {tab === "details" && <Details detail={detail} repositoryUrl={repositoryUrl} />}
    </div>
  );
}

function Details({ detail, repositoryUrl }: { detail: PipelineRunDetail; repositoryUrl: string | null }) {
  const params = Object.entries(detail.parameters);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel>
        <PanelHeader title="Parameters" />
        {params.length === 0 ? (
          <PanelBody className="text-[13px] text-secondary">This run took no parameters.</PanelBody>
        ) : (
          <dl className="divide-y divide-border-subtle">
            {params.map(([k, v]) => (
              <div key={k} className="flex gap-3 px-4 py-2 text-[13px]"><dt className="w-40 shrink-0 truncate font-mono text-secondary" title={k}>{k}</dt><dd className="min-w-0 break-all font-mono">{v}</dd></div>
            ))}
          </dl>
        )}
      </Panel>
      <Panel>
        <PanelHeader title="Changes" />
        {detail.changes.length === 0 ? (
          <PanelBody className="text-[13px] text-secondary">No new commits in this run.</PanelBody>
        ) : (
          <ul className="divide-y divide-border-subtle">
            {detail.changes.map((c) => (
              <li key={c.sha} className="flex min-w-0 items-baseline gap-3 px-4 py-2 text-[13px]">
                {repositoryUrl ? <a href={`${repositoryUrl}/commit/${c.sha}`} target="_blank" rel="noopener noreferrer" className="shrink-0 font-mono hover:underline underline-offset-4">{c.sha.slice(0, 7)}</a> : <span className="shrink-0 font-mono">{c.sha.slice(0, 7)}</span>}
                <span className="min-w-0 flex-1 truncate" title={c.message}>{c.message}</span>
                <span className="shrink-0 text-xs text-secondary">{c.author}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
