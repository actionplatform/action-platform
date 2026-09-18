"use client";

import { FileText, GitBranch, Layers, Rocket } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ActionField, ActionFields, ActionForm, ActionSteps, ActionSummary } from "@/components/ui/action-form";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Hint } from "@/components/ui/hint";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ReleasePreview } from "@/lib/api";
import { useAction } from "@/lib/use-action";
import { nextVersion, previewRelease, runRelease } from "@/features/releases/actions";
import type { AppView } from "@/features/projects";
import { RunAlert, summarize } from "@/features/deployments";

type Increment = "patch" | "minor" | "major";

const LEVELS: { id: Increment; label: string }[] = [
  { id: "patch", label: "Patch" },
  { id: "minor", label: "Minor" },
  { id: "major", label: "Major" },
];

export function bump(current: string, level: Increment): string {
  const m = current.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!m) return current;
  const [major, minor, patch] = [Number(m[1]), Number(m[2]), Number(m[3])];
  if (level === "major") return `${major + 1}.0.0`;
  if (level === "minor") return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}

export function withNotes(entry: string, notes: string): string {
  if (!notes.trim()) return entry;
  const lines = entry.split("\n");
  const head = lines.findIndex((l) => l.startsWith("#"));
  if (head < 0) return `${notes.trim()}\n\n${entry}`;
  return [...lines.slice(0, head + 1), "", notes.trim(), ...lines.slice(head + 1)].join("\n");
}

export function ReleaseCard({ view }: { view: AppView }) {
  const router = useRouter();
  const [level, setLevel] = useState<Increment>("patch");
  const [branch, setBranch] = useState(view.branch);
  const [showPreview, setShowPreview] = useState(false);
  const branches = view.branches.map((b) => b.name);
  const options = branches.includes(view.branch) ? branches : [view.branch, ...branches];
  const switching = branch !== view.branch;
  const selected = view.branches.find((b) => b.name === branch);
  const branchMissing = switching && !branches.includes(branch);

  const current = view.version ?? "0.0.0";
  const [computed, setComputed] = useState<{ next: string; prerelease: boolean } | null>(null);
  const stable = computed ? !computed.prerelease : view.stableBranches.includes(branch);
  useEffect(() => {
    let live = true;
    setComputed(null);
    nextVersion(view.registryId, level, switching ? branch : null).then((r) => {
      if (live && r.ok) setComputed({ next: r.data.next, prerelease: r.data.prerelease });
    });
    return () => { live = false; };
  }, [view.registryId, view.version, level, branch, switching]);
  const next = computed?.next ?? bump(current, level);
  const tagExists = view.tags.includes(`v${next}`);

  const [name, setName] = useState(`Release ${next}`);
  const [nameTouched, setNameTouched] = useState(false);
  const [notes, setNotes] = useState("");
  useEffect(() => { if (!nameTouched) setName(`Release ${next}`); }, [next, nameTouched]);

  const action = useAction<ReleasePreview, ReleasePreview>({
    preview: () => previewRelease(view.registryId, level, switching ? branch : null),
    run: () => runRelease(view.projectId, view.appId, view.registryId, level, switching ? branch : null, { name: name.trim() || null, notes: notes.trim() || null }),
    whileAway: "The release may have been cut anyway: check the tags before trying again.",
    onDone: () => { setNotes(""); setNameTouched(false); router.refresh(); },
  });

  useEffect(() => { if (action.step === "previewed") setShowPreview(true); }, [action.step]);

  const canRelease = view.can["app.release"] && view.workingTree === "clean" && (switching || view.health.ok) && !!view.repositoryUrl && !tagExists && !branchMissing;
  const blocker = !view.can["app.release"] ? "Your role cannot create releases." : !view.repositoryUrl ? "This app has no remote." : branchMissing ? `Branch ${branch} is not on the remote.` : tagExists ? `Tag v${next} already exists.` : view.workingTree !== "clean" ? (switching ? "Commit or discard the pending changes before switching branches." : "Commit or discard the pending changes first.") : !switching && !view.health.ok ? "Fix the branch policy problems first." : null;

  const change = (set: (v: string) => void) => (v: string) => { set(v); action.clearOutcome(); };
  const creating = action.step === "running";

  return (
    <ActionForm
      title="Create release"
      aside={<Hint text={stable ? "Stable version, published as the latest release." : `Pre-release (rc). Stable versions are cut from ${view.stableBranches[0] ?? "main"}.`}><Badge tone={stable ? "ok" : "neutral"}>{stable ? "Stable" : "Pre-release"}</Badge></Hint>}
      primary={{ label: `Create ${next}`, icon: Rocket, onClick: action.confirm, disabled: !canRelease, busy: creating, busyLabel: "Creating…" }}
      secondary={{ label: "Preview changelog", icon: FileText, onClick: action.preview, disabled: !view.repositoryUrl || !view.can["app.release"], busy: action.step === "previewing", busyLabel: "Loading…" }}
      blocker={action.error ? null : blocker}
      summary={[{ label: "Current", value: current }, { label: "Next", value: next }, { label: "Tag", value: `v${next}` }, { label: "Kind", value: stable ? "stable" : "pre-release (rc)" }]}
      alerts={
        <>
          {action.result && !action.result.dry_run && <RunAlert tone="success" title={`Released ${action.result.next}`} summary={`Tag v${action.result.next} pushed and published from ${action.result.branch}.`} />}
          {action.error && <RunAlert tone="danger" title="Release failed" summary={summarize(action.error)} log={action.error} />}
        </>
      }
      dialogs={
        <>
          <Dialog open={showPreview && !!action.previewed} onClose={() => setShowPreview(false)} title={`Preview ${action.previewed?.next ?? ""}`} description="Nothing is written until you create the release." className="max-w-2xl">
            {action.previewed && (
              <div className="space-y-4 text-sm">
                <ActionSummary columns={4} items={[{ label: "Current", value: action.previewed.current }, { label: "Next", value: action.previewed.next }, { label: "Branch", value: action.previewed.branch }, { label: "Tag", value: `v${action.previewed.next}` }]} />
                <div>
                  <div className="mb-1 text-xs text-secondary">Changelog</div>
                  <pre className="max-h-72 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">{withNotes(action.previewed.changelog || "No conventional commits since the last tag.", notes)}</pre>
                </div>
                {blocker && <div className="rounded-md border border-foreground px-3 py-2">{blocker}</div>}
              </div>
            )}
          </Dialog>

          <ConfirmDialog open={action.step === "confirming"} onClose={action.cancel} title={level === "major" ? `Create major release ${next}?` : `Create release ${next}?`} confirmLabel={creating ? "Creating…" : "Create release"} pending={action.busy} onConfirm={action.execute} danger={level === "major"}>
            {level === "major" && (
              <div className="mb-4 rounded-md border border-border border-l-2 border-l-status-warn px-3 py-2 text-sm">
                A major version signals breaking changes. <span className="text-secondary">{current} → {next} cannot be undone once published.</span>
              </div>
            )}
            <ActionSummary items={[{ label: "Repository", value: view.repository ?? "—" }]} className="grid-cols-1" />
            <ActionSummary className="mt-3 border-t border-border-subtle pt-3" items={[{ label: "Branch", value: branch }, { label: "Tag", value: `v${next}` }, { label: "Name", value: name.trim() || `Release ${next}` }, { label: "Kind", value: stable ? "stable" : "pre-release (rc)" }]} />
            <ActionSteps
              steps={[
                <>Bump LAST_VERSION and prepend CHANGELOG.md{notes.trim() ? " with your notes" : ""}</>,
                <>Commit <span className="font-mono text-foreground">chore(release): {next}</span> and tag it</>,
                <>Push and publish the release on {view.sourceKind === "github" ? "GitHub" : "the source host"}</>,
              ]}
            />
          </ConfirmDialog>
        </>
      }
    >
      <ActionFields>
        <ActionField label="Branch" hint={<Hint text={`Releases are cut from this branch. ${selected?.protected ? "Protected." : selected?.kind ? `A ${selected.kind} branch.` : ""}`} />}>
          <Select size="lg" mono icon={<GitBranch className="size-4" strokeWidth={1.75} />} value={branch} onChange={change(setBranch)} options={options.map((b) => ({ value: b, label: b, hint: view.stableBranches.includes(b) ? "stable" : "rc" }))} />
        </ActionField>
        <ActionField label="Version" hint={<Hint text="Patch fixes, minor adds, major breaks. The next version comes from the tags on the branch." />}>
          <Select size="lg" mono icon={<Layers className="size-4" strokeWidth={1.75} />} value={level} onChange={change((v) => setLevel(v as Increment))} options={LEVELS.map((l) => ({ value: l.id, label: `${l.label} · ${bump(current, l.id)}`, hint: l.id === level ? next : undefined }))} />
        </ActionField>
        <ActionField label="Name">
          <Input className="h-[42px] rounded-[7px]" value={name} onChange={(e) => { setName(e.target.value); setNameTouched(true); }} onBlur={() => { if (!name.trim()) { setNameTouched(false); setName(`Release ${next}`); } }} disabled={!view.can["app.release"]} />
        </ActionField>
        <ActionField label="Notes" hint={<><span className="text-muted-foreground">(optional)</span> <Hint text="Markdown. Goes under the version heading in CHANGELOG.md and on the code host, above the generated commit list." /></>}>
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What changed, in your words…" rows={2} className="min-h-[42px] rounded-[7px] font-mono text-[13px]" disabled={!view.can["app.release"]} />
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}
