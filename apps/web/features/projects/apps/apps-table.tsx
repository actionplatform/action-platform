"use client";

import { Layers } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, type PageState } from "@/components/ui/data-table";
import type { AppRow } from "@/lib/api";
import { RemoveButton } from "./remove-button";

type Item = { id: string; name: string; registryId: string; tearing: boolean };

export function AppsTable({ projectId, apps, paging, rows, manage }: { projectId: string; apps: Item[]; paging: PageState; rows: Record<string, AppRow>; manage: boolean }) {
  return (
    <DataTable
      title="Apps"
      rows={apps}
      paging={paging}
      pageKey="apps"
      rowKey={(a) => a.id}
      noun={["app", "apps"]}
      empty={{ icon: Layers, title: "No apps yet", text: "Create one with New app, from a template or an existing repository." }}
      columns={[
        {
          key: "name",
          label: "Name",
          width: 24,
          render: (a) => {
            const r = rows[a.registryId];
            return (
              <Cell title={[a.name, a.tearing && "tearing down", r && !r.exists && "missing", !r && "not on API"].filter(Boolean).join(" · ")}>
                <span className="inline-flex items-center gap-2 align-middle">
                  <Link href={`/projects/${projectId}/apps/${a.id}`} className="font-medium hover:underline underline-offset-4">{a.name}</Link>
                  {a.tearing && <Badge tone="warning">tearing down</Badge>}
                  {r && !r.exists && <Badge tone="bad">missing</Badge>}
                  {!r && <Badge>not on API</Badge>}
                </span>
              </Cell>
            );
          },
        },
        { key: "type", label: "Type", width: 9, hideBelow: "lg", render: (a) => <Cell muted>{rows[a.registryId]?.type ?? "—"}</Cell> },
        { key: "language", label: "Language", width: 11, hideBelow: "lg", render: (a) => <Cell muted>{rows[a.registryId]?.language ?? "—"}</Cell> },
        { key: "branch", label: "Branch", width: 14, render: (a) => <Cell mono muted>{rows[a.registryId]?.branch ?? "—"}</Cell> },
        { key: "version", label: "Version", width: 12, render: (a) => <Cell mono>{rows[a.registryId]?.last_version ?? "—"}</Cell> },
        { key: "repository", label: "Repository", width: 24, hideBelow: "lg", render: (a) => <Cell mono muted>{rows[a.registryId]?.url || "no remote"}</Cell> },
        ...(manage
          ? [{
              key: "actions",
              label: "Actions",
              width: 8,
              actions: true,
              render: (a: Item) => {
                const r = rows[a.registryId];
                return a.tearing ? null : <RemoveButton projectId={projectId} appId={a.id} name={a.name} repositoryUrl={r?.url || null} deployTarget={r?.deploy_target ?? null} />;
              },
            }]
          : []),
      ]}
    />
  );
}
