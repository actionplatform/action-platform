"use client";

import { ArrowUpRight, Check, ExternalLink, MoreHorizontal, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Menu } from "@/components/ui/menu";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";
import { syncApp } from "../actions";
import { DeleteAppDialog } from "../delete-app-dialog";
import type { AppView } from "./model";

type SyncStatus = "idle" | "syncing" | "success" | "error";

const BRANDS = { github: siGithub, gitlab: siGitlab, bitbucket: siBitbucket } as const;

export function AppHeader({ view }: { view: AppView }) {
  const router = useRouter();
  const [status, setStatus] = useState<SyncStatus>("idle");
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncedAt, setSyncedAt] = useState<number | null>(view.lastSyncedAt ? new Date(view.lastSyncedAt).getTime() : null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [now, setNow] = useState<number | null>(null);
  const [pending, start] = useTransition();

  useEffect(() => {
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);
  const brand = view.sourceKind && view.sourceKind in BRANDS ? BRANDS[view.sourceKind as keyof typeof BRANDS] : null;

  useEffect(() => {
    if (status !== "success") return;
    const t = setTimeout(() => setStatus("idle"), 2500);
    return () => clearTimeout(t);
  }, [status]);

  const sync = () =>
    start(async () => {
      setStatus("syncing");
      const r = await syncApp(view.projectId, view.appId, view.registryId);
      if (r.ok) { setSyncedAt(Date.now()); setStatus("success"); setSyncError(null); router.refresh(); } else { setStatus("error"); setSyncError(r.error); }
    });

  const syncLabel = status === "syncing" ? "Syncing..." : status === "success" ? "Synced" : status === "error" ? "Sync failed" : "Sync";
  const syncHint = status === "error" ? (syncError ?? "Try again") : status === "success" ? "Just now" : syncedAt ? (now ? `Last synced ${relativeTime(new Date(syncedAt), now)}` : "Last synced") : view.repositoryUrl ? "Never synced" : "No remote";

  return (
    <header>
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[13px] text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">Projects</Link>
        <span aria-hidden>/</span>
        <Link href={`/projects/${view.projectId}`} className="hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">{view.projectName}</Link>
        <span aria-hidden>/</span>
        <span aria-current="page" className="text-secondary">{view.name}</span>
      </nav>

      <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <h1 className="text-[28px] font-semibold leading-[34px] tracking-[-0.02em]">{view.name}</h1>
          {view.repository && (
            view.repositoryUrl ? (
              <a href={view.repositoryUrl} target="_blank" rel="noopener noreferrer" className="mt-1.5 inline-flex items-center gap-2 font-mono text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">
                {brand ? <BrandIcon icon={brand} mono className="size-4" /> : null}
                {view.repository}
                <ExternalLink className="size-3.5" strokeWidth={1.75} />
              </a>
            ) : (
              <div className="mt-1.5 inline-flex items-center gap-2 font-mono text-[13px] text-secondary">
                {brand ? <BrandIcon icon={brand} mono className="size-4" /> : null}
                {view.repository}
                <Badge className="h-5 px-2 text-[11px]">not pushed</Badge>
              </div>
            )
          )}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {view.labels.map((l) => <span key={l} className="flex h-[26px] items-center rounded-full border border-[#2d2d2d] px-2.5 text-xs text-secondary">{l}</span>)}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => sync()}
              disabled={status === "syncing" || !view.repositoryUrl || !view.can["app.sync"]}
              aria-live="polite"
              className={cn("flex h-[38px] min-w-[104px] items-center justify-center gap-2 rounded-[7px] border border-[#303030] px-3.5 text-sm text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground disabled:cursor-not-allowed disabled:opacity-60", status === "error" && "border-foreground")}
            >
              {status === "success" ? <Check className="size-4" strokeWidth={2} /> : <RefreshCw className={cn("size-4", status === "syncing" && "animate-spin")} strokeWidth={1.75} />}
              {syncLabel}
            </button>
            <span className={cn("hidden max-w-md text-[13px] sm:block", status === "error" ? "text-foreground" : "text-muted-foreground")}>{syncHint}</span>
          </div>

          <Menu
            label="Project actions"
            items={[
              ...(view.repositoryUrl ? [{ label: "Open repository", icon: <ArrowUpRight className="size-4" strokeWidth={1.75} />, onSelect: () => window.open(view.repositoryUrl!, "_blank", "noopener,noreferrer") }] : []),
              ...(view.can["project.manage"] ? ["separator" as const, { label: "Delete project", icon: <Trash2 className="size-4" strokeWidth={1.75} />, danger: true, onSelect: () => setConfirmDelete(true) }] : []),
            ]}
            trigger={({ open, toggle, id }) => (
              <button type="button" aria-label="More actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle} className="flex size-[38px] items-center justify-center rounded-[7px] border border-[#303030] text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
                <MoreHorizontal className="size-[18px]" strokeWidth={1.75} />
              </button>
            )}
          />
        </div>
      </div>

      <DeleteAppDialog open={confirmDelete} onClose={() => setConfirmDelete(false)} onDeleted={() => router.push(`/projects/${view.projectId}`)} projectId={view.projectId} appId={view.appId} name={view.name} repositoryUrl={view.repositoryUrl} />
    </header>
  );
}
