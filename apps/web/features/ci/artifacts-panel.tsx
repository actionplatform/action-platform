"use client";

import { Download, Package } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { call } from "@/lib/call";
import { type CiArtifact, artifactHref, bytes } from "@/lib/ci-kinds";
import { readCiArtifacts } from "./actions";

type Props = { projectId: string; appId: string; job: string; number: number };

export function ArtifactsPanel({ projectId, appId, job, number }: Props) {
  const [items, setItems] = useState<CiArtifact[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    call(() => readCiArtifacts(projectId, appId, job, number), (e) => ({ ok: false as const, error: e }), "Reload the page to list the artifacts again.").then((r) => {
      if (cancelled) return;
      if (r.ok) setItems(r.data);
      else setError(r.error);
    });
    return () => { cancelled = true; };
  }, [projectId, appId, job, number]);

  if (error) return <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>;
  if (items === null) return <Panel><div className="px-4 py-6 text-[13px] text-secondary">Listing the artifacts…</div></Panel>;
  if (items.length === 0) return <Panel><EmptyState icon={Package} title="No artifacts" text="This run archived no files." /></Panel>;

  return (
    <Panel>
      <PanelHeader title="Artifacts" description="Downloaded through the platform." />
      <ul className="divide-y divide-border-subtle">
        {items.map((a) => (
          <li key={a.path} className="flex min-w-0 items-center gap-3 px-4 py-2 text-[13px]">
            <span className="min-w-0 flex-1 truncate font-mono" title={a.path}>{a.path}</span>
            <span className="shrink-0 text-xs text-secondary">{bytes(a.size)}</span>
            <a href={artifactHref(projectId, appId, job, number, a.path)} download aria-label={`Download ${a.path}`} className="inline-flex size-8 shrink-0 items-center justify-center rounded-md hover:bg-surface-hover"><Download className="size-4" strokeWidth={1.75} /></a>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
