"use client";

import { Cloud, ExternalLink, ListChecks, Rocket, ShieldCheck, Tag } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActionField, ActionFields, ActionForm, ActionSummary, Running } from "@/components/ui/action-form";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Hint } from "@/components/ui/hint";
import { Select } from "@/components/ui/select";
import type { DeployResult } from "@/lib/api";
import type { ReadinessRow } from "@/lib/releases";
import { ACCEPTS, CRITICALITY, type Criticality, type Scope, shapeOf } from "@/lib/scope-kinds";
import { CriticalityBadge } from "@/features/scopes";
import { relativeTime } from "@/lib/time";
import { useAction } from "@/lib/use-action";
import { deployJob, startDeploy } from "@/features/deployments/actions";
import type { AppView } from "@/features/projects";
import { readiness as fetchReadiness } from "@/features/readiness/actions";
import { LiveLog } from "@/features/jobs";
import { RunAlert, summarize } from "./run-alert";

type Outcome = { dryRun: boolean; rows: DeployResult[] };

const versionOf = (tag: string) => tag.replace(/^v/, "");

export function DeployCard({ view, liveStages = [], scopes = [] }: { view: AppView; liveStages?: string[]; scopes?: Scope[] }) {
  const router = useRouter();
  const releases = view.tags.filter((t) => /^v?\d/.test(t));
  const [stage, setStage] = useState(scopes[0]?.name ?? "dev");
  const scope = scopes.find((s) => s.name === stage) ?? null;
  const target = scope?.target ?? (typeof view.deploy.target === "string" ? String(view.deploy.target) : null);
  const [tag, setTag] = useState(releases[0] ?? "");
  const [dryRun, setDryRun] = useState(false);
  const [force, setForce] = useState(false);
  const [readiness, setReadiness] = useState<ReadinessRow[] | null>(null);
  const dry = useRef(false);

  useEffect(() => {
    if (!tag) { setReadiness(null); return; }
    let alive = true;
    setReadiness(null);
    fetchReadiness(view.projectId, view.appId, tag).then((r) => { if (alive) setReadiness(r.ok ? r.data : []); });
    return () => { alive = false; };
  }, [tag, view.projectId, view.appId]);

  useEffect(() => { setForce(false); }, [tag, stage]);

  const ready = readiness?.find((r) => r.stage === stage) ?? null;
  const blocked = ready?.verdict === "blocked";
  const blockers = ready ? ready.checks.filter((c) => !c.ok && c.severity !== "warning") : [];
  const warnings = ready ? ready.checks.filter((c) => !c.ok && c.severity === "warning") : [];

  const poll = useCallback(
    async (job: string) => {
      const r = await deployJob(view.projectId, job);
      if (!r.ok) return r;
      const failed = r.data.results.find((x) => !x.ok);
      return { ok: true as const, data: { status: failed ? "failed" : r.data.status, outcome: { dryRun: dry.current, rows: r.data.results } as Outcome, error: r.data.error ?? failed?.error ?? null } };
    },
    [view.projectId],
  );

  const action = useAction<never, Outcome>({
    run: () => startDeploy(view.registryId, stage, dry.current, versionOf(tag), force),
    poll,
    onDone: () => router.refresh(),
  });

  const live = liveStages.includes(stage);
  const shape = tag ? shapeOf(tag) : null;
  const refused = !!scope && !!shape && !ACCEPTS[scope.criticality as Criticality]?.includes(shape);
  const canDeploy = !!target && !!scope && view.can["app.release"] && !!view.repositoryUrl && !!tag && !live && !refused && (!blocked || force);
  const blocker = scopes.length === 0 ? "Create a scope first: a deploy always lands on a scope." : !target ? "Pick a deploy target in Configuration or on the scope first." : !view.can["app.release"] ? "Your role cannot deploy." : !view.repositoryUrl ? "This app has no remote." : releases.length === 0 ? "A deploy ships a release: create one in Releases first." : live ? `A deploy to ${stage} is running — one at a time per scope.` : refused ? `${tag} is a ${shape} release; ${stage} is ${scope!.criticality} and takes ${ACCEPTS[scope!.criticality as Criticality].join(", ")} only.` : blocked && !force ? `${tag} is not deployable to ${stage}: fix the checks below, re-check on the release page, or deploy anyway.` : null;
  const timelineHref = `/projects/${view.projectId}/apps/${view.appId}/releases/${encodeURIComponent(tag)}`;

  const launch = (asDryRun: boolean) => {
    dry.current = asDryRun;
    setDryRun(asDryRun);
    action.clearOutcome();
    if (asDryRun) action.execute(); else action.confirm();
  };
  const kind = dryRun ? "Preflight" : "Deploy";
  const okRows = action.result?.rows ?? [];

  return (
    <ActionForm
      title="Deploy"
      aside={target ? <Badge className="font-mono">{target}</Badge> : <Badge>No target</Badge>}
      primary={{ label: `Deploy to ${stage}`, icon: Rocket, onClick: () => launch(false), disabled: !canDeploy, busy: action.busy && !dryRun, busyLabel: "Deploying…" }}
      secondary={{ label: "Run preflight", icon: ListChecks, onClick: () => launch(true), disabled: !canDeploy, busy: action.busy && dryRun, busyLabel: "Checking…" }}
      blocker={action.error ? null : blocker}
      summary={[{ label: "Target", value: target ?? "—" }, { label: "Release", value: tag ? `${tag} · ${shapeOf(tag)}` : "—" }, { label: "Scope", value: scope ? `${scope.name} · ${CRITICALITY[scope.criticality as Criticality]?.label ?? scope.criticality}` : "—" }, { label: "Version", value: tag ? versionOf(tag) : "—" }]}
      alerts={
        <>
          {tag && readiness !== null && (
            <div className={`rounded-lg border px-3 py-2 text-[13px] ${blocked ? "border-status-bad/30 bg-status-bad/5" : ready?.verdict === "ok" ? "border-status-ok/30 bg-status-ok/5" : "border-border bg-surface"}`}>
              <div className="flex flex-wrap items-center gap-2">
                <ShieldCheck className={`size-4 ${blocked ? "text-status-bad" : ready?.verdict === "ok" ? "text-status-ok" : "text-secondary"}`} strokeWidth={1.75} />
                <span className="font-medium">
                  {!ready ? `${tag} was not checked for ${stage} yet.` : ready.verdict === "pending" ? `Checking ${tag} for ${stage}…` : blocked ? `${tag} is blocked for ${stage}.` : `${tag} is ready for ${stage}.`}
                </span>
                {ready?.checked_at && <span className="text-secondary">checked {relativeTime(ready.checked_at)}</span>}
                <Link href={timelineHref} className="ml-auto text-secondary underline-offset-4 hover:text-foreground hover:underline">Details</Link>
              </div>
              {blockers.length > 0 && (
                <ul className="mt-2 space-y-1 text-status-bad">
                  {blockers.slice(0, 4).map((c, i) => <li key={`${c.id}-${i}`}><span className="font-mono text-xs">{c.id}</span> — {c.detail}{c.fix && <span className="text-secondary"> · {c.fix}</span>}</li>)}
                </ul>
              )}
              {warnings.length > 0 && !blocked && (
                <ul className="mt-2 space-y-1 text-status-warn">
                  {warnings.slice(0, 3).map((c, i) => <li key={`${c.id}-${i}`}><span className="font-mono text-xs">{c.id}</span> — {c.detail}</li>)}
                </ul>
              )}
              {blocked && (
                <label className="mt-2 flex items-center gap-2 text-[13px]">
                  <input type="checkbox" className="size-4 accent-foreground" checked={force} onChange={(e) => setForce(e.target.checked)} />
                  Deploy anyway — I understand the checks failed.
                </label>
              )}
            </div>
          )}
          {action.busy && action.step === "polling" && <Running label={dryRun ? "Preflight running" : "Deploying"} detail={`${versionOf(tag)} → ${stage}`} />}
          {action.job && <LiveLog jobId={action.job} live={action.step === "polling"} title={dryRun ? "Preflight log" : "Deploy log"} />}
          {action.error && <RunAlert tone="danger" title={`${kind} failed`} summary={summarize(action.error)} log={action.error} />}
          {okRows.map((row) => <RunAlert key={row.target} tone="success" title={action.result?.dryRun ? "Preflight passed" : "Deployed"} summary={`${row.target} · ${row.version}${row.url ? ` · ${row.url}` : ""}`} />)}
          {okRows.some((r) => r.url) && (
            <div className="flex flex-wrap gap-3 text-[13px]">
              {okRows.filter((r) => r.url).map((r) => <a key={r.target} href={r.url!} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">{r.url} <ExternalLink className="size-3" strokeWidth={1.75} /></a>)}
            </div>
          )}
        </>
      }
      dialogs={
        <ConfirmDialog open={action.step === "confirming"} onClose={action.cancel} title={`Deploy ${view.name} ${versionOf(tag)} to ${stage}?`} confirmLabel={`Deploy ${versionOf(tag)}`} pending={action.busy} onConfirm={action.execute}>
          <ActionSummary items={[{ label: "Target", value: target ?? "—" }, { label: "Scope", value: stage }, { label: "Release", value: tag }, { label: "Version", value: versionOf(tag) }]} />
          <p className="mt-4 text-sm text-secondary">Checks out the tag, builds and runs the target for real on the platform&apos;s worker. Run preflight first to check credentials and the template without changing anything.</p>
        </ConfirmDialog>
      }
    >
      <ActionFields>
        <ActionField label="Release" hint={<Hint text="A deploy always ships a tagged release — the tag is checked out, built and deployed; the working tree never is." />}>
          {releases.length > 0 ? (
            <Select size="lg" mono icon={<Tag className="size-4" strokeWidth={1.75} />} value={tag} onChange={(v) => { setTag(v); action.clearOutcome(); }} options={releases.map((t, i) => ({ value: t, label: versionOf(t), hint: i === 0 ? "latest" : undefined }))} />
          ) : (
            <div className="flex h-[42px] items-center rounded-[7px] border border-dashed border-border px-3 font-mono text-sm text-muted-foreground">No releases yet</div>
          )}
        </ActionField>
        <ActionField label="Scope" hint={<Hint text="Where the release lands. The scope's criticality decides which releases it takes: test and low take candidates, medium and above take stable and hotfix releases." />}>
          {scopes.length > 0 ? (
            <Select size="lg" mono icon={<Cloud className="size-4" strokeWidth={1.75} />} value={stage} onChange={(v) => { setStage(v); action.clearOutcome(); }} options={scopes.map((s) => ({ value: s.name, label: s.name, hint: `${s.kind} · ${CRITICALITY[s.criticality as Criticality]?.label ?? s.criticality}` }))} />
          ) : (
            <div className="flex h-[42px] items-center rounded-[7px] border border-dashed border-border px-3 font-mono text-sm text-muted-foreground">No scopes yet</div>
          )}
          {scope && <div className="mt-1.5 flex items-center gap-2 text-xs text-secondary"><CriticalityBadge value={scope.criticality} className="h-5 px-1.5 text-[11px]" /> accepts {ACCEPTS[scope.criticality as Criticality]?.join(" · ")}</div>}
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}
