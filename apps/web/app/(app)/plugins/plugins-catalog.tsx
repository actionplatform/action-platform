"use client";

import { BadgeCheck, Check, Copy, ExternalLink, Package, Puzzle, Search, Tag } from "lucide-react";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
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
};

const field = "h-11 rounded-[9px] border border-border bg-surface text-sm text-foreground";

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

function PluginCard({ item }: { item: PluginItem }) {
  return (
    <article className="flex flex-col rounded-[9px] border border-border bg-surface p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-[42px] shrink-0 items-center justify-center rounded-lg border border-[#292929] bg-[#0e0e0e]"><Puzzle className="size-[22px] text-secondary" strokeWidth={1.5} /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-[15px] font-semibold">{item.slug}</h3>
            {item.verified && <Badge tone="ok" className="gap-1"><BadgeCheck className="size-3" strokeWidth={2} /> Verified</Badge>}
            {item.installed && <Badge tone={item.enabled ? "inverse" : "neutral"}>{item.enabled ? "On this platform" : "Installed, disabled"}</Badge>}
          </div>
          <p className="mt-1 text-[13px] text-secondary">{item.description}</p>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
        <div><dt className="text-muted-foreground">Package</dt><dd className="mt-0.5 truncate font-mono">{item.pypi}</dd></div>
        <div><dt className="text-muted-foreground">Latest</dt><dd className="mt-0.5 font-mono">{item.latest || "—"}{item.min_core && <span className="text-secondary"> · core ≥ {item.min_core}</span>}</dd></div>
      </dl>

      {item.needs.length > 0 && (
        <div className="mt-3">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Needs</div>
          <ul className="mt-1 space-y-0.5 text-[12px] text-secondary">
            {item.needs.map((n) => <li key={n} className="font-mono">{n}</li>)}
          </ul>
        </div>
      )}

      {item.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {item.tags.map((t) => <Badge key={t} className="gap-1"><Tag className="size-3" strokeWidth={1.75} />{t}</Badge>)}
        </div>
      )}

      <div className="mt-auto pt-4">
        <InstallCommand slug={item.slug} />
        <div className="mt-2 flex gap-3 text-[12px]">
          {item.repo && <a href={item.repo} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">Repository <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
          {item.pypi && <a href={`https://pypi.org/project/${item.pypi}/`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground"><Package className="size-3" strokeWidth={1.75} /> PyPI</a>}
        </div>
      </div>
    </article>
  );
}

export function PluginsCatalog({ plugins, index }: { plugins: PluginItem[]; index: string }) {
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
        description="Extensions for the CLI and the MCP server — deploy targets, overlays, tools, release strategies. Installed with the CLI on each machine; the hosted platform runs only the ones its operator installed."
      />

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
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((p) => <PluginCard key={p.slug} item={p} />)}
            </div>
          )}
        </>
      )}
    </>
  );
}
