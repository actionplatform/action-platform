"use client";

import { Cloud, ExternalLink, ListChecks, Rocket, Tag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Hint } from "@/components/ui/hint";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { DeployResult } from "@/lib/api";
import { deployJob, startDeploy } from "@/features/deployments/actions";
import type { AppView } from "@/features/projects";
import { RunAlert, summarize } from "./run-alert";

const STAGES = [
  { value: "dev", label: "dev", hint: "default" },
  { value: "prod", label: "prod", hint: "stable" },
];

type Run = { job: string; dryRun: boolean };
type Outcome = { dryRun: boolean; rows: DeployResult[]; error: string | null };

const versionOf = (tag: string) => tag.replace(/^v/, "");

export function DeployCard({ view, liveStages = [] }: { view: AppView; liveStages?: string[] }) {
  const router = useRouter();
  const target = typeof view.deploy.target === "string" ? String(view.deploy.target) : null;
  const releases = view.tags.filter((t) => /^v?\d/.test(t));
  const [stage, setStage] = useState("dev");
  const [tag, setTag] = useState(releases[0] ?? "");
  const [confirm, setConfirm] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const busy = pending || run !== null;
  const live = liveStages.includes(stage);
  const canDeploy = !!target && view.can["app.release"] && !!view.repositoryUrl && !!tag && !live;
  const blocker = !target ? "Pick a deploy target in Configuration first." : !view.can["app.release"] ? "Your role cannot deploy." : !view.repositoryUrl ? "This app has no remote." : releases.length === 0 ? "A deploy ships a release: create one in Releases first." : live ? `A deploy to ${stage} is running — one at a time per environment.` : null;

  useEffect(() => {
    if (!run) return;
    const timer = setInterval(async () => {
      const r = await deployJob(view.projectId, run.job);
      if (!r.ok) { setError(r.error); setRun(null); return; }
      if (r.data.status === "done") { setOutcome({ dryRun: run.dryRun, rows: r.data.results, error: null }); setRun(null); }
      if (r.data.status === "failed") { setOutcome({ dryRun: run.dryRun, rows: [], error: r.data.error ?? "failed" }); setRun(null); }
    }, 2000);
    return () => clearInterval(timer);
  }, [run, view.projectId]);

  const launch = (dryRun: boolean) =>
    start(async () => {
      setError(null);
      setOutcome(null);
      const r = await startDeploy(view.registryId, stage, dryRun, versionOf(tag));
      setConfirm(false);
      if (r.ok) { setRun({ job: r.data.job, dryRun }); router.refresh(); } else setError(r.error);
    });

  const failedRow = outcome?.rows.find((r) => !r.ok) ?? null;
  const failure = outcome ? outcome.error ?? failedRow?.error ?? null : null;
  const kind = outcome?.dryRun ? "Preflight" : "Deploy";
  const okRows = outcome && !failure ? outcome.rows : [];

  return (
    <Panel>
      <PanelHeader title="Deploy" aside={target ? <Badge className="font-mono">{target}</Badge> : <Badge>Not configured</Badge>} />
      <PanelBody className="space-y-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-secondary">Release <Hint text="A deploy always ships a tagged release — the tag is checked out, built and deployed; the working tree never is." /></div>
            {releases.length > 0 ? (
              <Select size="lg" mono icon={<Tag className="size-4" strokeWidth={1.75} />} value={tag} onChange={(v) => { setTag(v); setOutcome(null); }} options={releases.map((t, i) => ({ value: t, label: versionOf(t), hint: i === 0 ? "latest" : undefined }))} />
            ) : (
              <div className="flex h-[42px] items-center rounded-[7px] border border-dashed border-border px-3 font-mono text-sm text-muted-foreground">No releases yet</div>
            )}
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-secondary">Environment <Hint text="The worker runs the target with a token signed for this app; credentials come from the cloud, never from the platform." /></div>
            <Select size="lg" mono icon={<Cloud className="size-4" strokeWidth={1.75} />} value={stage} onChange={(v) => { setStage(v); setOutcome(null); }} options={STAGES} />
          </div>
        </div>
        {run && (
          <div className="flex items-center gap-3 rounded-md border border-border border-l-2 border-l-status-warn bg-surface px-3 py-2.5 text-sm">
            <span className="size-2 animate-pulse rounded-full bg-status-warn" />
            <span className="font-medium">{run.dryRun ? "Preflight running" : "Deploying"}</span>
            <span className="text-secondary">{versionOf(tag)} → {stage}</span>
          </div>
        )}
        {failure && <RunAlert tone="danger" title={`${kind} failed`} summary={summarize(failure)} log={failure} />}
        {okRows.length > 0 && okRows.map((row) => (
          <RunAlert key={row.target} tone="success" title={outcome?.dryRun ? "Preflight passed" : "Deployed"} summary={`${row.target} · ${row.version}${row.url ? ` · ${row.url}` : ""}`} />
        ))}
        {okRows.some((r) => r.url) && (
          <div className="flex flex-wrap gap-3 text-[13px]">
            {okRows.filter((r) => r.url).map((r) => <a key={r.target} href={r.url!} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">{r.url} <ExternalLink className="size-3" strokeWidth={1.75} /></a>)}
          </div>
        )}
        {error && <RunAlert tone="danger" title="Could not start" summary={summarize(error)} log={error} />}

        <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:items-center">
          <Button className="w-full sm:w-auto" disabled={busy || !canDeploy} onClick={() => setConfirm(true)}><Rocket className="size-4" strokeWidth={1.75} /> {run && !run.dryRun ? "Deploying…" : `Deploy to ${stage}`}</Button>
          <Button className="w-full sm:w-auto" variant="outline" disabled={busy || !canDeploy} onClick={() => launch(true)}><ListChecks className="size-4" strokeWidth={1.75} /> {run?.dryRun ? "Checking…" : "Run preflight"}</Button>
          {blocker && !error && <div className="text-[13px] text-muted-foreground sm:ml-auto">{blocker}</div>}
        </div>
      </PanelBody>

      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={`Deploy ${view.name} ${versionOf(tag)} to ${stage}?`}
        confirmLabel={`Deploy ${versionOf(tag)}`}
        pending={busy}
        onConfirm={() => launch(false)}
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div><dt className="text-xs text-secondary">Target</dt><dd className="font-mono text-[13px]">{target}</dd></div>
          <div><dt className="text-xs text-secondary">Environment</dt><dd className="font-mono text-[13px]">{stage}</dd></div>
          <div><dt className="text-xs text-secondary">Release</dt><dd className="font-mono text-[13px]">{tag}</dd></div>
          <div><dt className="text-xs text-secondary">Version</dt><dd className="font-mono text-[13px]">{versionOf(tag)}</dd></div>
        </dl>
        <p className="mt-4 text-sm text-secondary">Checks out the tag, builds and runs the target for real on the platform&apos;s worker. Run preflight first to check credentials and the template without changing anything.</p>
      </ConfirmDialog>
    </Panel>
  );
}
