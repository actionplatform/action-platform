"use client";

import {
  ArrowRight,
  Check,
  FileText,
  GitBranch,
  Rocket,
  ShieldCheck,
} from "lucide-react";
import { call } from "@/lib/call";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { ReleasePreview } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  nextVersion,
  previewRelease,
  runRelease,
} from "@/features/releases/actions";
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
  return [
    ...lines.slice(0, head + 1),
    "",
    notes.trim(),
    ...lines.slice(head + 1),
  ].join("\n");
}

export function ReleaseCard({ view }: { view: AppView }) {
  const router = useRouter();
  const [level, setLevel] = useState<Increment>("patch");
  const [preview, setPreview] = useState<ReleasePreview | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState<ReleasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [creating, setCreating] = useState(false);

  const [branch, setBranch] = useState(view.branch);
  const branches = view.branches.map((b) => b.name);
  const options = branches.includes(view.branch)
    ? branches
    : [view.branch, ...branches];
  const switching = branch !== view.branch;
  const selected = view.branches.find((b) => b.name === branch);
  const branchMissing = switching && !branches.includes(branch);

  const current = view.version ?? "0.0.0";
  const [computed, setComputed] = useState<{
    next: string;
    prerelease: boolean;
  } | null>(null);
  const stable = computed
    ? !computed.prerelease
    : view.stableBranches.includes(branch);
  useEffect(() => {
    let live = true;
    setComputed(null);
    nextVersion(view.registryId, level, switching ? branch : null).then((r) => {
      if (live && r.ok)
        setComputed({ next: r.data.next, prerelease: r.data.prerelease });
    });
    return () => {
      live = false;
    };
  }, [view.registryId, view.version, level, branch, switching]);
  const next = computed?.next ?? bump(current, level);
  const tagExists = view.tags.includes(`v${next}`);

  const [name, setName] = useState(`Release ${next}`);
  const [nameTouched, setNameTouched] = useState(false);
  const [notes, setNotes] = useState("");
  useEffect(() => {
    if (!nameTouched) setName(`Release ${next}`);
  }, [next, nameTouched]);

  const canRelease =
    view.can["app.release"] &&
    view.workingTree === "clean" &&
    (switching || view.health.ok) &&
    !!view.repositoryUrl &&
    !tagExists &&
    !branchMissing;
  const blocker = !view.can["app.release"]
    ? "Your role cannot create releases."
    : !view.repositoryUrl
      ? "This app has no remote."
      : branchMissing
        ? `Branch ${branch} is not on the remote.`
        : tagExists
          ? `Tag v${next} already exists.`
          : view.workingTree !== "clean"
            ? switching
              ? "Commit or discard the pending changes before switching branches."
              : "Commit or discard the pending changes first."
            : !switching && !view.health.ok
              ? "Fix the branch policy problems first."
              : null;

  const loadPreview = () =>
    start(async () => {
      setError(null);
      const r = await previewRelease(
        view.registryId,
        level,
        switching ? branch : null,
      );
      if (r.ok) {
        setPreview(r.data);
        setShowPreview(true);
      } else setError(r.error);
    });

  const create = () => {
    setCreating(true);
    start(async () => {
      setError(null);
      const r = await call(
        () =>
          runRelease(
            view.projectId,
            view.appId,
            view.registryId,
            level,
            switching ? branch : null,
            { name: name.trim() || null, notes: notes.trim() || null },
          ),
        (error) => ({ ok: false as const, error }),
        "The release may have been cut anyway: check the tags before trying again.",
      );
      setConfirm(false);
      setCreating(false);
      if (r.ok) {
        setResult(r.data);
        setPreview(null);
        setNotes("");
        setNameTouched(false);
        router.refresh();
      } else setError(r.error);
    });
  };

  return (
    <Panel>
      <PanelHeader
        title="Create release"
        aside={
          <Hint
            text={
              stable
                ? "Stable version, published as the latest release."
                : `Pre-release (rc). Stable versions are cut from ${view.stableBranches[0] ?? "main"}.`
            }
          >
            <Badge tone={stable ? "ok" : "neutral"}>
              {stable ? "Stable" : "Pre-release"}
            </Badge>
          </Hint>
        }
      />
      <PanelBody className="space-y-5">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:gap-0">
          <div className="space-y-5 border-b border-border-subtle pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-6">
            <div className="space-y-2">
              <div className="text-xs text-secondary">Branch</div>
              <div className="flex flex-wrap items-center gap-3">
                <Select
                  size="lg"
                  mono
                  className="w-full sm:w-64"
                  icon={<GitBranch className="size-4" strokeWidth={1.75} />}
                  value={branch}
                  onChange={(v) => {
                    setBranch(v);
                    setPreview(null);
                    setResult(null);
                  }}
                  options={options.map((b) => ({
                    value: b,
                    label: b,
                    hint: view.stableBranches.includes(b) ? "stable" : "rc",
                  }))}
                />
                <Hint text="Releases are cut from this branch.">
                  <Badge
                    tone={selected?.protected ? "ok" : "neutral"}
                    className="gap-1"
                  >
                    <ShieldCheck className="size-3" strokeWidth={2} />
                    {selected?.protected
                      ? "Protected"
                      : selected?.kind
                        ? `${selected.kind} branch`
                        : "Branch"}
                  </Badge>
                </Hint>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-secondary">Version</div>
              <div className="flex flex-wrap items-center gap-4">
                <div
                  role="radiogroup"
                  aria-label="Version increment"
                  className="grid h-10 w-full grid-cols-3 overflow-hidden rounded-[7px] border border-border sm:inline-flex sm:w-auto"
                >
                  {LEVELS.map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      role="radio"
                      aria-checked={level === l.id}
                      onClick={() => {
                        setLevel(l.id);
                        setPreview(null);
                      }}
                      className={cn(
                        "px-4 text-sm transition-colors focus-visible:outline-none focus-visible:bg-surface-hover",
                        level === l.id
                          ? "bg-surface-selected text-foreground"
                          : "text-secondary hover:text-foreground",
                      )}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2 font-mono">
                  <span className="text-sm text-secondary">{current}</span>
                  <ArrowRight
                    className="size-4 text-muted-foreground"
                    strokeWidth={1.75}
                  />
                  <span className="text-lg font-semibold">{next}</span>
                </div>
              </div>
            </div>
          </div>
          <div className="space-y-5 lg:pl-6">
            <label className="block space-y-2">
              <span className="block text-xs text-secondary">Name</span>
              <Input
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setNameTouched(true);
                }}
                onBlur={() => {
                  if (!name.trim()) {
                    setNameTouched(false);
                    setName(`Release ${next}`);
                  }
                }}
                disabled={!view.can["app.release"]}
              />
            </label>

            <label className="block space-y-2">
              <span className="flex items-center gap-1.5 text-xs text-secondary">
                Notes <span className="text-muted-foreground">(optional)</span>{" "}
                <Hint text="Markdown. Goes under the version heading in CHANGELOG.md and on the code host, above the generated commit list." />
              </span>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What changed, in your words…"
                rows={3}
                className="font-mono text-[13px]"
                disabled={!view.can["app.release"]}
              />
            </label>
          </div>
        </div>

        {result && !result.dry_run && (
          <RunAlert
            tone="success"
            title={`Released ${result.next}`}
            summary={`Tag v${result.next} pushed and published from ${result.branch}.`}
          />
        )}
        {error && (
          <RunAlert
            tone="danger"
            title="Release failed"
            summary={summarize(error)}
            log={error}
          />
        )}

        <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:items-center">
          <Button
            className="w-full sm:w-auto"
            disabled={pending || creating || !canRelease}
            onClick={() => setConfirm(true)}
          >
            {creating ? (
              <span className="size-3.5 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground" />
            ) : (
              <Rocket className="size-4" strokeWidth={1.75} />
            )}{" "}
            {creating ? "Creating…" : `Create ${next}`}
          </Button>
          <Button
            className="w-full sm:w-auto"
            variant="outline"
            disabled={
              pending ||
              creating ||
              !view.repositoryUrl ||
              !view.can["app.release"]
            }
            onClick={loadPreview}
          >
            <FileText className="size-4" strokeWidth={1.75} />{" "}
            {pending && !confirm && !creating
              ? "Loading…"
              : "Preview changelog"}
          </Button>
          {blocker && !error && (
            <div className="text-[13px] text-muted-foreground sm:ml-auto">
              {blocker}
            </div>
          )}
        </div>
      </PanelBody>

      <Dialog
        open={showPreview && !!preview}
        onClose={() => setShowPreview(false)}
        title={`Preview ${preview?.next ?? ""}`}
        description="Nothing is written until you create the release."
        className="max-w-2xl"
      >
        {preview && (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
              <Item k="Current" v={preview.current} />
              <Item k="Next" v={preview.next} />
              <Item k="Branch" v={preview.branch} />
              <Item k="Tag" v={`v${preview.next}`} />
            </dl>
            <div>
              <div className="mb-1 text-xs text-secondary">Changelog</div>
              <pre className="max-h-72 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-xs whitespace-pre-wrap">
                {withNotes(
                  preview.changelog ||
                    "No conventional commits since the last tag.",
                  notes,
                )}
              </pre>
            </div>
            {blocker && (
              <div className="rounded-md border border-foreground px-3 py-2">
                {blocker}
              </div>
            )}
          </div>
        )}
      </Dialog>

      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={
          level === "major"
            ? `Create major release ${next}?`
            : `Create release ${next}?`
        }
        confirmLabel={creating ? "Creating…" : "Create release"}
        pending={pending || creating}
        onConfirm={create}
        danger={level === "major"}
      >
        {level === "major" && (
          <div className="mb-4 rounded-md border border-border border-l-2 border-l-status-warn px-3 py-2 text-sm">
            A major version signals breaking changes.{" "}
            <span className="text-secondary">
              {current} → {next} cannot be undone once published.
            </span>
          </div>
        )}
        <dl className="text-sm">
          <Item k="Repository" v={view.repository ?? "—"} />
        </dl>
        <dl className="mt-3 grid grid-cols-[repeat(2,minmax(0,1fr))] gap-x-4 gap-y-3 border-t border-border-subtle pt-3 text-sm">
          <Item k="Branch" v={branch} />
          <Item k="Tag" v={`v${next}`} />
          <Item k="Name" v={name.trim() || `Release ${next}`} />
          <Item k="Kind" v={stable ? "stable" : "pre-release (rc)"} />
        </dl>
        <div className="mt-4 border-t border-border-subtle pt-3">
          <div className="text-xs text-secondary">This will</div>
          <div className="mt-2 space-y-1.5 text-sm text-secondary">
            <div className="flex items-start gap-2">
              <Check
                className="mt-0.5 size-4 shrink-0"
                strokeWidth={2}
                aria-hidden="true"
              />
              <span className="min-w-0">
                Bump LAST_VERSION and prepend CHANGELOG.md
                {notes.trim() ? " with your notes" : ""}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Check
                className="mt-0.5 size-4 shrink-0"
                strokeWidth={2}
                aria-hidden="true"
              />
              <span className="min-w-0">
                Commit{" "}
                <span className="font-mono text-foreground">
                  chore(release): {next}
                </span>{" "}
                and tag it
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Check
                className="mt-0.5 size-4 shrink-0"
                strokeWidth={2}
                aria-hidden="true"
              />
              <span className="min-w-0">
                Push and publish the release on{" "}
                {view.sourceKind === "github" ? "GitHub" : "the source host"}
              </span>
            </div>
          </div>
        </div>
      </ConfirmDialog>
    </Panel>
  );
}

function Item({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-secondary">{k}</dt>
      <dd className="truncate font-mono text-[13px] text-foreground" title={v}>
        {v}
      </dd>
    </div>
  );
}
