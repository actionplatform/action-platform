"use client";

import { ExternalLink, GitPullRequest, RefreshCw, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { call } from "@/lib/call";
import { installJob, startInstall } from "./actions";
import { type AdoptionRow, type InstallResult, type InstallRun, selectable, stateLabel, toOpen } from "./model";

type Options = { types: { id: string; label: string }[] };
type Job = { id: string; dryRun: boolean; status: string; result: InstallRun | null; error: string | null };

const CI = [
  { value: "", label: "Detect CI" },
  { value: "github", label: "GitHub Actions" },
  { value: "gitlab", label: "GitLab CI" },
  { value: "jenkins", label: "Jenkins" },
  { value: "bitbucket", label: "Bitbucket Pipelines" },
  { value: "none", label: "No CI files" },
];

const LANGUAGES = [
  { value: "", label: "Detect language" },
  ...["python", "node", "go", "php", "java", "rust", "ruby"].map((l) => ({ value: l, label: l })),
  { value: "none", label: "No language" },
];

export function AdoptionView({ projectId, rows, canManage, options }: { projectId: string; rows: AdoptionRow[]; canManage: boolean; options: Options }) {
  const router = useRouter();
  const [picked, setPicked] = useState<Set<string>>(() => new Set(rows.filter(selectable).map((r) => r.app_id)));
  const [type, setType] = useState(options.types.find((t) => t.id === "web")?.id ?? options.types[0]?.id ?? "web");
  const [ci, setCi] = useState("");
  const [language, setLanguage] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [preview, setPreview] = useState<InstallRun | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const running = !!job && job.status !== "done" && job.status !== "failed";
  const opening = useMemo(() => toOpen(preview), [preview]);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const timer = setInterval(async () => {
      const r = await call(() => installJob(projectId, job.id), (error) => ({ ok: false as const, error }));
      if (!r.ok) return;
      setJob({ ...job, ...r.data });
      if (r.data.status === "done") {
        if (job.dryRun) setPreview(r.data.result);
        router.refresh();
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, projectId, router]);

  const run = (dryRun: boolean, apps: string[]) => start(async () => {
    setError(null);
    setPreview(null);
    const r = await call(() => startInstall(projectId, { apps, type, ci: ci || null, language: language || null, code: "platform", dry_run: dryRun }), (error) => ({ ok: false as const, error }), "The run may have started anyway: reload before trying again.");
    setConfirming(false);
    if (r.ok) setJob({ id: r.data.job, dryRun, status: "queued", result: null, error: null });
    else setError(r.error);
  });

  const toggle = (id: string) => setPicked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const allPicked = rows.length > 0 && rows.every((r) => picked.has(r.app_id));

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader
          title={`Apps · ${rows.length}`}
          description="Where each app stands, as the last check or install run found it."
          aside={rows.length > 0 && canManage && <button type="button" className="text-xs text-secondary hover:text-foreground" onClick={() => setPicked(allPicked ? new Set() : new Set(rows.map((r) => r.app_id)))}>{allPicked ? "Clear" : "Select all"}</button>}
        />
        <ul className="divide-y divide-border">
          {rows.length === 0 && <li className="px-4 py-6 text-center text-sm text-secondary">No apps in this project.</li>}
          {rows.map((r) => {
            const state = stateLabel(r);
            return (
              <li key={r.app_id} className="flex items-start gap-3 px-4 py-3">
                {canManage && <input id={`adopt-${r.app_id}`} type="checkbox" aria-label={`Select ${r.name}`} className="mt-1 size-4 shrink-0 accent-foreground" checked={picked.has(r.app_id)} onChange={() => toggle(r.app_id)} />}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    <Link href={`/projects/${projectId}/apps/${r.app_id}`} className="hover:underline underline-offset-4">{r.name}</Link>
                    <Badge tone={state.tone} className="max-w-full truncate" title={state.label}>{state.label}</Badge>
                    {r.pull_request?.url && <a href={r.pull_request.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-secondary underline underline-offset-4 hover:text-foreground">Open pull request <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
                  </div>
                  <div className="mt-0.5 text-[13px] text-secondary">{[r.language && `language ${r.language}`, r.ci && `CI ${r.ci}`, r.version && `version ${r.version}`].filter(Boolean).join(" · ") || "Not checked yet"}</div>
                </div>
              </li>
            );
          })}
        </ul>
      </Panel>

      {canManage ? (
        <Panel>
          <PanelHeader title="Install selected" description="Previews each app's plan first; the pull requests open only after you confirm. Apps that already have platform.toml or an open install pull request are skipped." />
          <PanelBody className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Select value={type} onChange={setType} aria-label="Project type" options={options.types.map((t) => ({ value: t.id, label: t.label }))} />
              <Select value={ci} onChange={setCi} aria-label="CI" options={CI} />
              <Select value={language} onChange={setLanguage} aria-label="Language" options={LANGUAGES} />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-secondary">{picked.size} {picked.size === 1 ? "app" : "apps"} selected. Commits go to <span className="font-mono">chore/platform</span> on each repository.</p>
              <Button disabled={picked.size === 0 || pending || running} onClick={() => run(true, [...picked])}><ScanSearch className="size-4" strokeWidth={1.75} /> Install selected</Button>
            </div>
            {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
            {running && <p className="flex items-center gap-2 text-sm text-secondary"><RefreshCw className="size-4 animate-spin" strokeWidth={1.75} aria-hidden="true" />{job.dryRun ? "Cloning each repository and planning the install…" : "Committing and opening the pull requests…"} This page updates by itself.</p>}
            {job?.error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{job.error}</div>}
          </PanelBody>
        </Panel>
      ) : (
        <Panel><PanelBody className="text-sm text-secondary">Opening install pull requests needs a role that manages projects.</PanelBody></Panel>
      )}

      {preview && <Results run={preview} />}
      {preview && opening.length > 0 && !running && job?.dryRun && (
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button onClick={() => setConfirming(true)}><GitPullRequest className="size-4" strokeWidth={1.75} /> Open {opening.length} pull {opening.length === 1 ? "request" : "requests"}</Button>
        </div>
      )}
      {job && !job.dryRun && job.result && <Results run={job.result} />}

      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={`Open ${opening.length} install pull ${opening.length === 1 ? "request" : "requests"}?`}
        description="Each repository gets a commit on chore/platform with the files in its plan and a pull request against its base branch. Nothing merges by itself."
        confirmLabel="Open pull requests"
        pending={pending}
        onConfirm={() => run(false, opening.map((a) => a.app_id))}
      />
    </div>
  );
}

function Results({ run }: { run: InstallRun }) {
  return (
    <Panel>
      <PanelHeader title={run.dry_run ? "Plans" : "Results"} description={run.dry_run ? "Nothing was written. Confirm to open the pull requests." : `${run.opened} opened · ${run.skipped} skipped · ${run.failed} failed`} />
      <ul className="divide-y divide-border">
        {run.apps.map((a) => <ResultRow key={a.app_id} result={a} />)}
      </ul>
    </Panel>
  );
}

function ResultRow({ result }: { result: InstallResult }) {
  const state = stateLabel(result);
  const plan = result.plan;
  return (
    <li className="space-y-2 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center gap-2 font-medium">
        {result.name}
        <Badge tone={state.tone} className="max-w-full truncate" title={state.label}>{state.label}</Badge>
        {result.skipped && <Badge>skipped</Badge>}
        {result.pull_request?.url && <a href={result.pull_request.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-secondary underline underline-offset-4 hover:text-foreground">Open pull request <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
      </div>
      {plan && (
        <dl className="grid gap-x-6 gap-y-1 text-[13px] text-secondary sm:grid-cols-2">
          <div><dt className="inline">Language </dt><dd className="inline font-mono text-foreground">{plan.language || "none"}</dd></div>
          <div><dt className="inline">CI </dt><dd className="inline font-mono text-foreground">{plan.ci}</dd>{plan.detected_ci.length > 0 && <span> · detected {plan.detected_ci.join(", ")}</span>}</div>
          <div><dt className="inline">Version </dt><dd className="inline font-mono text-foreground">{plan.version}</dd>{plan.version_source && <span> · from {plan.version_source}</span>}</div>
          <div><dt className="inline">Branch </dt><dd className="inline font-mono text-foreground">{plan.branch}</dd><span> → {plan.base}</span></div>
          <div className="sm:col-span-2"><dt className="inline">Creates </dt><dd className="inline font-mono text-foreground">{plan.created.join(", ") || "nothing"}</dd></div>
          {plan.kept.length > 0 && <div className="sm:col-span-2"><dt className="inline">Keeps </dt><dd className="inline font-mono">{plan.kept.join(", ")}</dd></div>}
          {plan.warnings.map((w) => <div key={w} className="sm:col-span-2 text-status-warn">{w}</div>)}
        </dl>
      )}
    </li>
  );
}
