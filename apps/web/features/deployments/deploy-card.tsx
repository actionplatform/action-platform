"use client";

import { Cloud, ExternalLink, ListChecks, Rocket, Tag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { ActionField, ActionFields, ActionForm, ActionSummary, Running } from "@/components/ui/action-form";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Hint } from "@/components/ui/hint";
import { Select } from "@/components/ui/select";
import type { DeployResult } from "@/lib/api";
import { useAction } from "@/lib/use-action";
import { deployJob, startDeploy } from "@/features/deployments/actions";
import type { AppView } from "@/features/projects";
import { RunAlert, summarize } from "./run-alert";

const STAGES = [
  { value: "dev", label: "dev", hint: "default" },
  { value: "prod", label: "prod", hint: "stable" },
];

type Outcome = { dryRun: boolean; rows: DeployResult[] };

const versionOf = (tag: string) => tag.replace(/^v/, "");

export function DeployCard({ view, liveStages = [] }: { view: AppView; liveStages?: string[] }) {
  const router = useRouter();
  const target = typeof view.deploy.target === "string" ? String(view.deploy.target) : null;
  const releases = view.tags.filter((t) => /^v?\d/.test(t));
  const [stage, setStage] = useState("dev");
  const [tag, setTag] = useState(releases[0] ?? "");
  const [dryRun, setDryRun] = useState(false);
  const dry = useRef(false);

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
    run: () => startDeploy(view.registryId, stage, dry.current, versionOf(tag)),
    poll,
    onDone: () => router.refresh(),
  });

  const live = liveStages.includes(stage);
  const canDeploy = !!target && view.can["app.release"] && !!view.repositoryUrl && !!tag && !live;
  const blocker = !target ? "Pick a deploy target in Configuration first." : !view.can["app.release"] ? "Your role cannot deploy." : !view.repositoryUrl ? "This app has no remote." : releases.length === 0 ? "A deploy ships a release: create one in Releases first." : live ? `A deploy to ${stage} is running — one at a time per environment.` : null;

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
      aside={target ? <Badge className="font-mono">{target}</Badge> : <Badge>Not configured</Badge>}
      primary={{ label: `Deploy to ${stage}`, icon: Rocket, onClick: () => launch(false), disabled: !canDeploy, busy: action.busy && !dryRun, busyLabel: "Deploying…" }}
      secondary={{ label: "Run preflight", icon: ListChecks, onClick: () => launch(true), disabled: !canDeploy, busy: action.busy && dryRun, busyLabel: "Checking…" }}
      blocker={action.error ? null : blocker}
      alerts={
        <>
          {action.busy && action.step === "polling" && <Running label={dryRun ? "Preflight running" : "Deploying"} detail={`${versionOf(tag)} → ${stage}`} />}
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
          <ActionSummary items={[{ label: "Target", value: target ?? "—" }, { label: "Environment", value: stage }, { label: "Release", value: tag }, { label: "Version", value: versionOf(tag) }]} />
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
        <ActionField label="Environment" hint={<Hint text="The worker runs the target with a token signed for this app; credentials come from the cloud, never from the platform." />}>
          <Select size="lg" mono icon={<Cloud className="size-4" strokeWidth={1.75} />} value={stage} onChange={(v) => { setStage(v); action.clearOutcome(); }} options={STAGES} />
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}
