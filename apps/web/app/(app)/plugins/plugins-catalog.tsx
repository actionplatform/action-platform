"use client";

import { BadgeCheck, Check, ChevronRight, Copy, ExternalLink, Globe, KeyRound, Package, Puzzle, RotateCw, Search, Tag, Wrench } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useState, useTransition } from "react";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { call } from "@/lib/call";
import { cn } from "@/lib/utils";
import { installPlugin, pluginJob, removePlugin, restartPlatform, setPluginEnabled } from "./actions";
import { PluginsNoneState, PluginsNoResults } from "./plugins-states";

export type PluginItem = {
  slug: string;
  description: string;
  author: string;
  verified: boolean;
  repo: string;
  pypi: string;
  latest: string;
  min_core: string;
  needs: string[];
  tags: string[];
  installed: boolean;
  installed_version?: string | null;
  enabled: boolean;
  restart_pending?: boolean;
};

const field = "h-11 rounded-[9px] border border-border bg-surface text-sm text-foreground";
const NONE = /^(nothing|none|no external)/i;

type Requirement = { kind: "tools" | "environment" | "network" | "other"; label: string; text: string };

const KINDS: Record<Requirement["kind"], { label: string; icon: typeof Wrench; preview: string }> = {
  tools: { label: "Tools", icon: Wrench, preview: "" },
  environment: { label: "Environment", icon: KeyRound, preview: "environment" },
  network: { label: "Network", icon: Globe, preview: "network" },
  other: { label: "Other", icon: Puzzle, preview: "other" },
};

function parseNeeds(needs: string[]): Requirement[] {
  return needs
    .filter((n) => n.trim() && !NONE.test(n.replace(/^[a-z]+:\s*/i, "")))
    .map((n) => {
      const m = n.match(/^([a-z]+):\s*(.*)$/i);
      const key = (m?.[1] ?? "").toLowerCase();
      const text = (m?.[2] ?? n).trim();
      const kind: Requirement["kind"] = key === "tool" || key === "tools" ? "tools" : key === "env" || key === "environment" ? "environment" : key === "net" || key === "network" ? "network" : "other";
      return { kind, label: KINDS[kind].label, text };
    });
}

function preview(rows: Requirement[]): string {
  const parts: string[] = [];
  for (const r of rows) {
    if (r.kind === "tools") parts.push(...r.text.split(",").map((t) => t.trim().split(/\s|\(/)[0]).filter(Boolean));
    else parts.push(KINDS[r.kind].preview);
  }
  return [...new Set(parts)].join(" · ");
}

function Requirements({ needs }: { needs: string[] }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const rows = useMemo(() => parseNeeds(needs), [needs]);
  const count = rows.length;

  return (
    <div className="mt-3">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        disabled={count === 0}
        className={cn(
          "flex h-12 w-full min-w-0 items-center gap-2.5 rounded-[8px] border border-[#292929] bg-[#121212] px-3 text-left text-sm transition-colors",
          count > 0 ? "cursor-pointer hover:bg-[#181818] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/[0.12]" : "cursor-default",
        )}
      >
        <ChevronRight className={cn("size-4 shrink-0 text-secondary transition-transform duration-150", open && "rotate-90")} strokeWidth={1.75} />
        <span className="shrink-0 font-medium">Requirements</span>
        {count === 0 ? (
          <span className="truncate text-secondary">No external requirements</span>
        ) : (
          <>
            <span className="shrink-0 text-secondary">{count} {count === 1 ? "requirement" : "requirements"}</span>
            <span className="ml-auto hidden min-w-0 truncate font-mono text-[12px] text-secondary sm:block">{preview(rows)}</span>
          </>
        )}
      </button>
      {open && count > 0 && (
        <div id={id} className="select-in mt-1.5 space-y-2.5 rounded-[8px] border border-[#292929] bg-[#0e0e0e] px-3 py-3">
          {rows.map((r, i) => {
            const Icon = KINDS[r.kind].icon;
            return (
              <div key={i} className="min-w-0">
                <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground"><Icon className="size-3" strokeWidth={1.75} />{r.label}</div>
                <div className="mt-0.5 break-words font-mono text-[12px] text-foreground/90">{r.text}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function InstallCommand({ slug }: { slug: string }) {
  const [copied, setCopied] = useState(false);
  const command = `action-platform plugin install ${slug}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <button type="button" onClick={copy} title="Copy" className="flex h-9 w-full items-center gap-2 rounded-[8px] border border-border bg-background px-3 font-mono text-[12px] transition-colors hover:border-border-hover">
      <span className="truncate">{command}</span>
      {copied ? <Check className="ml-auto size-3.5 shrink-0" strokeWidth={2.5} /> : <Copy className="ml-auto size-3.5 shrink-0 text-secondary" strokeWidth={1.75} />}
    </button>
  );
}

function useJob(onDone: () => void) {
  const [job, setJob] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!job) return;
    const timer = setInterval(async () => {
      const r = await call(() => pluginJob(job), (error) => ({ ok: false as const, error }), "The job may still be running.");
      if (!r.ok) { setError(r.error); setJob(null); return; }
      if (r.data.status === "done") { setJob(null); onDone(); }
      if (r.data.status === "failed") { setError(r.data.error ?? "failed"); setJob(null); onDone(); }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, onDone]);
  return { job, setJob, error, setError };
}

function HostedActions({ item }: { item: PluginItem }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [confirm, setConfirm] = useState<"install" | "remove" | null>(null);
  const { job, setJob, error, setError } = useJob(() => router.refresh());
  const busy = pending || job !== null;
  const run = (fn: () => Promise<{ ok: true; data: { job: string } } | { ok: false; error: string }>) =>
    start(async () => {
      setError(null);
      const r = await fn();
      if (r.ok) setJob(r.data.job); else setError(r.error);
      setConfirm(null);
    });
  const toggle = () =>
    start(async () => {
      setError(null);
      const r = await setPluginEnabled(item.slug, !item.enabled);
      if (!r.ok) setError(r.error); else router.refresh();
    });

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      {!item.installed && <Button size="sm" disabled={busy} onClick={() => setConfirm("install")}>{job ? "Installing…" : "Install on platform"}</Button>}
      {item.installed && (
        <>
          <Button size="sm" variant="outline" disabled={busy} onClick={toggle}>{item.enabled ? "Disable" : "Enable"}</Button>
          {item.latest && item.installed_version && item.latest !== item.installed_version && <Button size="sm" variant="outline" disabled={busy} onClick={() => setConfirm("install")}>Update to {item.latest}</Button>}
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirm("remove")}>{job ? "Working…" : "Remove"}</Button>
        </>
      )}
      {error && <span className="basis-full text-xs text-secondary">{error}</span>}
      <ConfirmDialog
        open={confirm === "install"}
        onClose={() => setConfirm(null)}
        onConfirm={() => run(() => installPlugin(item.slug))}
        title={item.installed ? `Update ${item.slug} to ${item.latest}?` : `Install ${item.slug} on this platform?`}
        description={<>pip installs <span className="font-mono">{item.pypi}=={item.latest}</span> into the platform&apos;s plugins volume. {item.installed ? "The running processes keep the current version until a restart." : "It loads without a restart."} No sandbox: the code runs inside the API and the worker.</>}
        confirmLabel={item.installed ? "Update" : "Install"}
        pending={busy}
      >
        {item.needs.length > 0 && <ul className="mt-2 space-y-1 font-mono text-xs text-secondary">{item.needs.map((n) => <li key={n}>{n}</li>)}</ul>}
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm === "remove"}
        onClose={() => setConfirm(null)}
        onConfirm={() => run(() => removePlugin(item.slug))}
        title={`Remove ${item.slug}?`}
        description="The package leaves the plugins volume and the plugin is disabled at once; what is already loaded stays until a restart."
        confirmLabel="Remove"
        danger
        pending={busy}
      />
    </div>
  );
}

function PluginCard({ item, hosted, canManage }: { item: PluginItem; hosted: boolean; canManage: boolean }) {
  return (
    <article className="flex flex-col rounded-[9px] border border-border bg-surface p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-[42px] shrink-0 items-center justify-center rounded-lg border border-[#292929] bg-[#0e0e0e]"><Puzzle className="size-[22px] text-secondary" strokeWidth={1.5} /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-[15px] font-semibold">{item.slug}</h3>
            {item.verified && <Badge tone="ok" className="gap-1"><BadgeCheck className="size-3" strokeWidth={2} /> Verified</Badge>}
            {item.installed && <Badge tone={item.enabled ? "inverse" : "neutral"}>{item.enabled ? "On this platform" : "Installed, disabled"}</Badge>}
            {item.restart_pending && <Badge className="gap-1"><RotateCw className="size-3" strokeWidth={1.75} /> Restart required</Badge>}
          </div>
          <p className="mt-1 text-[13px] text-secondary">{item.description}</p>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
        <div><dt className="text-muted-foreground">Package</dt><dd className="mt-0.5 truncate font-mono">{item.pypi}</dd></div>
        <div><dt className="text-muted-foreground">Latest</dt><dd className="mt-0.5 font-mono">{item.latest || "—"}{item.min_core && <span className="text-secondary"> · core ≥ {item.min_core}</span>}</dd></div>
      </dl>

      <Requirements needs={item.needs} />

      {item.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {item.tags.map((t) => <Badge key={t} className="gap-1"><Tag className="size-3" strokeWidth={1.75} />{t}</Badge>)}
        </div>
      )}

      <div className="mt-auto pt-4">
        <InstallCommand slug={item.slug} />
        {hosted && canManage && <HostedActions item={item} />}
        <div className="mt-2 flex gap-3 text-[12px]">
          {item.repo && <a href={item.repo} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">Repository <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
          {item.pypi && <a href={`https://pypi.org/project/${item.pypi}/`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground"><Package className="size-3" strokeWidth={1.75} /> PyPI</a>}
        </div>
      </div>
    </article>
  );
}

function RestartBanner({ slugs, canManage }: { slugs: string[]; canManage: boolean }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [note, setNote] = useState<string | null>(null);
  if (slugs.length === 0) return null;
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3 rounded-[9px] border border-border bg-surface px-[18px] py-3 text-sm">
      <RotateCw className="size-4 shrink-0 text-secondary" strokeWidth={1.75} />
      <span><span className="font-medium">Restart required</span> <span className="text-secondary">— {slugs.length} {slugs.length === 1 ? "change is" : "changes are"} waiting: {slugs.join(", ")}. Updates and removals take effect after a restart.</span></span>
      {canManage && <Button size="sm" variant="outline" className="ml-auto" disabled={pending} onClick={() => setOpen(true)}>Restart platform</Button>}
      {note && <span className="basis-full text-xs text-secondary">{note}</span>}
      <ConfirmDialog
        open={open}
        onClose={() => setOpen(false)}
        onConfirm={() => start(async () => { const r = await restartPlatform(); setNote(r.ok ? "Restarting — the platform is back in a few seconds." : r.error); setOpen(false); })}
        title="Restart the platform?"
        description="The API and the worker exit and come back with the changes loaded. Requests in flight are lost; a job running on the worker is retried."
        confirmLabel="Restart"
        pending={pending}
      />
    </div>
  );
}

export function PluginsCatalog({ plugins, index, hosted, restartPending, canManage }: { plugins: PluginItem[]; index: string; hosted: boolean; restartPending: string[]; canManage: boolean }) {
  const [search, setSearch] = useState("");
  const [tag, setTag] = useState("all");
  const tags = useMemo(() => [...new Set(plugins.flatMap((p) => p.tags))].sort(), [plugins]);
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return plugins.filter((p) => (tag === "all" || p.tags.includes(tag)) && (!q || [p.slug, p.description, p.pypi, p.author, ...p.tags, ...p.needs].some((s) => s.toLowerCase().includes(q))));
  }, [plugins, search, tag]);

  return (
    <>
      <PageHeader
        title="Plugins"
        badge={<Badge className="h-[26px] bg-surface px-2.5 text-xs font-medium">{plugins.length} {plugins.length === 1 ? "plugin" : "plugins"}</Badge>}
        description={hosted ? "Extensions for the CLI, the MCP server and this platform — deploy targets, overlays, tools, release strategies. Verified plugins install here without a restart; updates and removals restart." : "Extensions for the CLI and the MCP server — deploy targets, overlays, tools, release strategies. Installed with the CLI on each machine; this platform has no plugins volume (AP_PLUGINS_DIR)."}
      />

      <RestartBanner slugs={restartPending} canManage={canManage} />

      {plugins.length === 0 ? (
        <PluginsNoneState />
      ) : (
        <>
          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <label className="relative flex-1">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-secondary" strokeWidth={1.75} />
              <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search plugins..." className={cn(field, "w-full pl-10 pr-3.5 placeholder:text-muted-foreground focus:border-[#525252] focus:outline-none focus:ring-2 focus:ring-white/[0.06]")} />
            </label>
            <div className="flex flex-wrap gap-1.5">
              {["all", ...tags].map((t) => (
                <button key={t} type="button" onClick={() => setTag(t)} aria-pressed={tag === t} className={cn("h-11 rounded-[9px] border px-3.5 text-sm", tag === t ? "border-foreground text-foreground" : "border-border text-secondary hover:text-foreground")}>{t === "all" ? "All" : t}</button>
              ))}
            </div>
          </div>

          <div className="mt-[22px] mb-3.5 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Index</h2>
            <p role="status" aria-live="polite" className="text-[13px] text-secondary">{visible.length} {visible.length === 1 ? "result" : "results"} · <a href={index} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">actionplatform/plugins-index</a></p>
          </div>

          {visible.length === 0 ? (
            <PluginsNoResults onClear={() => { setSearch(""); setTag("all"); }} />
          ) : (
            <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((p) => <PluginCard key={p.slug} item={p} hosted={hosted} canManage={canManage} />)}
            </div>
          )}
        </>
      )}
    </>
  );
}
