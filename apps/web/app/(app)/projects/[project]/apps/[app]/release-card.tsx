"use client";

import { GitBranch, Rocket } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { ReleasePreview } from "@/lib/api";
import { bump, type Increment } from "@/lib/semver";
import { cn } from "@/lib/utils";
import { previewRelease, runRelease } from "../actions";
import type { AppView } from "./model";

const LEVELS: { id: Increment; label: string }[] = [
  { id: "patch", label: "Patch" },
  { id: "minor", label: "Minor" },
  { id: "major", label: "Major" },
];

export function ReleaseCard({ view }: { view: AppView }) {
  const router = useRouter();
  const [level, setLevel] = useState<Increment>("patch");
  const [preview, setPreview] = useState<ReleasePreview | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState<ReleasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const [branch, setBranch] = useState(view.branch);
  const branches = view.branches.map((b) => b.name);
  const options = branches.includes(view.branch) ? branches : [view.branch, ...branches];
  const stable = branch === "main" || branch === "master";
  const switching = branch !== view.branch;
  const stableBranch = options.find((b) => b === "main" || b === "master") ?? null;

  const current = view.version ?? "0.0.0";
  const localNext = bump(current, level);
  const next = preview && !preview.dry_run ? preview.next : stable ? localNext : `${localNext}-rc.N`;
  const canRelease = view.can["app.release"] && view.workingTree === "clean" && (switching || view.health.ok) && !!view.repositoryUrl;
  const blocker = !view.can["app.release"] ? "Your role cannot create releases." : !view.repositoryUrl ? "Push the repository to a remote first." : view.workingTree !== "clean" ? (switching ? "Commit or discard local changes before switching branches." : "Commit or discard local changes first.") : !switching && !view.health.ok ? "Fix the branch policy problems first." : null;

  const loadPreview = () =>
    start(async () => {
      setError(null);
      try { setPreview(await previewRelease(view.registryId, level, switching ? branch : null)); setShowPreview(true); } catch (e) { setError((e as Error).message); }
    });

  const create = () =>
    start(async () => {
      setError(null);
      try {
        const r = await runRelease(view.projectId, view.appId, view.registryId, level, switching ? branch : null);
        setResult(r);
        setConfirm(false);
        router.refresh();
      } catch (e) {
        setError((e as Error).message);
        setConfirm(false);
      }
    });

  return (
    <Panel>
      <PanelHeader title="Release" aside={<Badge tone={stable ? "ok" : "neutral"}>{stable ? "Stable" : "Pre-release"}</Badge>} />
      <PanelBody className="space-y-5">
        <div className="space-y-2">
          <div className="text-xs text-secondary">Branch</div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Select size="lg" mono className="sm:w-64" icon={<GitBranch className="size-4" strokeWidth={1.75} />} value={branch} onChange={(v) => { setBranch(v); setPreview(null); setResult(null); }} options={options.map((b) => ({ value: b, label: b, hint: b === "main" || b === "master" ? "stable" : "rc" }))} />
            <div className="text-[13px] text-secondary">{stable ? "Stable version, published as the latest release." : `Pre-release (rc). Stable versions are cut from ${stableBranch ?? "main"}.`}{switching && <> The workspace switches to <span className="font-mono text-foreground">{branch}</span> first.</>}</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-secondary">Increment</div>
          <div className="flex flex-wrap items-center gap-4">
            <div role="radiogroup" aria-label="Version increment" className="inline-flex h-10 overflow-hidden rounded-[7px] border border-border">
              {LEVELS.map((l) => (
                <button
                  key={l.id}
                  type="button"
                  role="radio"
                  aria-checked={level === l.id}
                  onClick={() => { setLevel(l.id); setPreview(null); }}
                  className={cn("px-4 text-sm transition-colors focus-visible:outline-none focus-visible:bg-surface-hover", level === l.id ? "bg-surface-selected text-foreground" : "text-secondary hover:text-foreground")}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <div className="font-mono text-[22px] font-semibold leading-7"><span className="text-secondary">{current}</span> <span className="text-muted-foreground">→</span> {next}</div>
          </div>
        </div>

        {result && !result.dry_run && (
          <div className="rounded-md border border-border-subtle bg-background px-3 py-2 text-sm">Released <span className="font-mono">{result.next}</span>.</div>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}

        <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:items-center">
          <Button disabled={pending || !canRelease} onClick={() => setConfirm(true)}><Rocket className="size-4" strokeWidth={1.75} /> Create {next}</Button>
          <Button variant="outline" disabled={pending || !view.repositoryUrl || !view.can["app.release"]} onClick={loadPreview}>{pending && !confirm ? "Loading…" : "Preview changelog"}</Button>
          {blocker && !error && <div className="text-[13px] text-muted-foreground sm:ml-auto">{blocker}</div>}
        </div>
      </PanelBody>

      <Dialog open={showPreview && !!preview} onClose={() => setShowPreview(false)} title={`Preview ${preview?.next ?? ""}`} description="Nothing is written until you create the release." className="max-w-2xl">
        {preview && (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
              <Item k="Current" v={preview.current} /><Item k="Next" v={preview.next} /><Item k="Branch" v={preview.branch} /><Item k="Tag" v={`v${preview.next}`} />
            </dl>
            <div>
              <div className="mb-1 text-xs text-secondary">Changelog</div>
              <pre className="max-h-72 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{preview.changelog || "No conventional commits since the last tag."}</pre>
            </div>
            {blocker && <div className="rounded-md border border-foreground px-3 py-2">{blocker}</div>}
          </div>
        )}
      </Dialog>

      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={`Create release ${next}?`}
        confirmLabel={`Create ${next}`}
        pending={pending}
        onConfirm={create}
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <Item k="Repository" v={view.repository ?? "—"} />
          <Item k="Branch" v={branch} />
          <Item k="Kind" v={stable ? "stable" : "pre-release (rc)"} />
          <Item k="Tag" v={`v${next}`} />
        </dl>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-secondary">
          <li>Bump LAST_VERSION and prepend CHANGELOG.md</li>
          <li>Commit <span className="font-mono">chore(release): {next}</span> and tag it</li>
          <li>Push and publish the release on {view.sourceKind === "github" ? "GitHub" : "the source host"}</li>
        </ul>
      </ConfirmDialog>
    </Panel>
  );
}

function Item({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-xs text-secondary">{k}</dt>
      <dd className="font-mono text-[13px]">{v}</dd>
    </div>
  );
}
