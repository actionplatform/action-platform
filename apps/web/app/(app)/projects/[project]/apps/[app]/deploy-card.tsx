"use client";

import { Cloud, ExternalLink, Tag } from "lucide-react";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { DeployResult } from "@/lib/api";
import { deployJob, startDeploy } from "../actions";
import type { AppView } from "./model";

const STAGES = [
  { value: "dev", label: "dev", hint: "default" },
  { value: "prod", label: "prod", hint: "stable" },
];

type Run = { job: string; dryRun: boolean };

const versionOf = (tag: string) => tag.replace(/^v/, "");

export function DeployCard({ view }: { view: AppView }) {
  const target = typeof view.deploy.target === "string" ? String(view.deploy.target) : null;
  const releases = view.tags.filter((t) => /^v?\d/.test(t));
  const [stage, setStage] = useState("dev");
  const [tag, setTag] = useState(releases[0] ?? "");
  const [confirm, setConfirm] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [results, setResults] = useState<{ dryRun: boolean; rows: DeployResult[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const busy = pending || run !== null;
  const canDeploy = !!target && view.can["app.release"] && !!view.repositoryUrl && !!tag;
  const blocker = !target ? "Pick a deploy target in Configuration first." : !view.can["app.release"] ? "Your role cannot deploy." : !view.repositoryUrl ? "This app has no remote." : releases.length === 0 ? "A deploy ships a release: create one in Releases first." : null;

  useEffect(() => {
    if (!run) return;
    const timer = setInterval(async () => {
      const r = await deployJob(view.projectId, run.job);
      if (!r.ok) { setError(r.error); setRun(null); return; }
      if (r.data.status === "done") { setResults({ dryRun: run.dryRun, rows: r.data.results }); setRun(null); }
      if (r.data.status === "failed") { setError(r.data.error ?? "failed"); setRun(null); }
    }, 2000);
    return () => clearInterval(timer);
  }, [run, view.projectId]);

  const launch = (dryRun: boolean) =>
    start(async () => {
      setError(null);
      setResults(null);
      const r = await startDeploy(view.registryId, stage, dryRun, versionOf(tag));
      setConfirm(false);
      if (r.ok) setRun({ job: r.data.job, dryRun }); else setError(r.error);
    });

  return (
    <Panel>
      <PanelHeader title="Deploy" aside={target ? <Badge className="font-mono">{target}</Badge> : <Badge>Not configured</Badge>} />
      <PanelBody className="space-y-5">
        <div className="space-y-2">
          <div className="text-xs text-secondary">Release</div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {releases.length > 0 ? (
              <Select size="lg" mono className="sm:w-64" icon={<Tag className="size-4" strokeWidth={1.75} />} value={tag} onChange={(v) => { setTag(v); setResults(null); }} options={releases.map((t, i) => ({ value: t, label: versionOf(t), hint: i === 0 ? "latest" : undefined }))} />
            ) : (
              <div className="font-mono text-sm text-muted-foreground">No releases yet</div>
            )}
            <div className="text-[13px] text-secondary">A deploy always ships a tagged release — the tag is checked out, built and deployed; the working tree never is.</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-secondary">Stage</div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Select size="lg" mono className="sm:w-64" icon={<Cloud className="size-4" strokeWidth={1.75} />} value={stage} onChange={(v) => { setStage(v); setResults(null); }} options={STAGES} />
            <div className="text-[13px] text-secondary">The worker runs the target with a token signed for this app; credentials come from the cloud, never from the platform.</div>
          </div>
        </div>

        {run && <div className="rounded-md border border-border-subtle bg-background px-3 py-2 text-sm">{run.dryRun ? "Preflight running…" : "Deploying…"}</div>}
        {results && (
          <ul className="space-y-2 text-sm">
            {results.rows.length === 0 && <li className="text-secondary">No deploy target answered.</li>}
            {results.rows.map((row) => (
              <li key={row.target} className="flex flex-wrap items-center gap-2 rounded-md border border-border-subtle bg-background px-3 py-2">
                <Badge tone={row.ok ? "ok" : "bad"}>{row.ok ? (results.dryRun ? "Preflight ok" : "Deployed") : "Failed"}</Badge>
                <span className="font-mono">{row.target}</span>
                {row.version && <span className="font-mono text-secondary">{row.version}</span>}
                {row.url && <a href={row.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">{row.url} <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
                {row.error && <span className="basis-full break-words font-mono text-xs text-secondary">{row.error}</span>}
              </li>
            ))}
          </ul>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm break-words">{error}</div>}

        <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:items-center">
          <Button disabled={busy || !canDeploy} onClick={() => setConfirm(true)}><Cloud className="size-4" strokeWidth={1.75} /> Deploy {tag ? versionOf(tag) : ""} to {stage}</Button>
          <Button variant="outline" disabled={busy || !canDeploy} onClick={() => launch(true)}>{run?.dryRun ? "Checking…" : "Preflight"}</Button>
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
          <div><dt className="text-xs text-secondary">Release</dt><dd className="font-mono text-[13px]">{tag}</dd></div>
          <div><dt className="text-xs text-secondary">Version</dt><dd className="font-mono text-[13px]">{versionOf(tag)}</dd></div>
          <div><dt className="text-xs text-secondary">Stage</dt><dd className="font-mono text-[13px]">{stage}</dd></div>
        </dl>
        <p className="mt-4 text-sm text-secondary">Checks out the tag, builds and runs the target for real on the platform&apos;s worker. Run Preflight first to check credentials and the template without changing anything.</p>
      </ConfirmDialog>
    </Panel>
  );
}
