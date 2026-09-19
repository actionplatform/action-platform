"use client";

import { MoreHorizontal, Target } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Cell, DataTable } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { ACCEPTS, type Criticality, type Scope } from "@/lib/scope-kinds";
import { CriticalityBadge } from "./criticality-badge";
import { deleteScope } from "./actions";

export function ScopesTable({ scopes, projectId, appId, canEdit, newHref }: { scopes: Scope[]; projectId: string; appId: string; canEdit: boolean; newHref?: string | null }) {
  const router = useRouter();
  const [removing, setRemoving] = useState<Scope | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const actions = (s: Scope) => [
    ...(canEdit ? [{ label: "Edit", onSelect: () => router.push(`${newHref?.replace(/\/new$/, "") ?? ""}/${encodeURIComponent(s.name)}`) }] : []),
    ...(canEdit ? [{ label: "Delete", onSelect: () => { setError(null); setRemoving(s); } }] : []),
  ];

  return (
    <>
      <DataTable
        title="Scopes"
        description="Where this app's releases are deployed. Criticality decides which releases a scope accepts."
        rows={scopes}
        rowKey={(s) => s.id}
        noun={["scope", "scopes"]}
        newHref={canEdit ? newHref : null}
        newLabel="New scope"
        empty={{ icon: Target, title: "No scopes yet", text: "Create one with New scope; a deploy always lands on a scope." }}
        minWidth={820}
        columns={[
          { key: "name", label: "Scope", width: 20, render: (s) => <span className="flex items-center gap-2"><span className="font-mono font-medium">{s.name}</span>{s.derived && <Badge className="h-5 px-1.5 text-[11px]">from config</Badge>}</span> },
          { key: "kind", label: "Kind", width: 10, render: (s) => <Cell mono>{s.kind}</Cell> },
          { key: "criticality", label: "Criticality", width: 14, render: (s) => <CriticalityBadge value={s.criticality} /> },
          { key: "accepts", label: "Accepts", width: 20, hide: "md", render: (s) => <Cell muted>{(ACCEPTS[s.criticality as Criticality] ?? []).join(" · ")}</Cell> },
          { key: "target", label: "Target", width: 16, hide: "sm", render: (s) => <Cell mono muted>{s.target ?? "—"}</Cell> },
          { key: "run_by", label: "Run by", width: 14, hide: "md", render: (s) => <Cell muted>{s.run_by}</Cell> },
          { key: "actions", label: "", width: 6, align: "right", render: (s) => actions(s).length > 0 ? <Menu label={`Actions for ${s.name}`} items={actions(s)} trigger={({ toggle, open, id }) => <Button size="icon" variant="ghost" aria-label={`Actions for ${s.name}`} aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle}><MoreHorizontal className="size-4" strokeWidth={1.75} /></Button>} /> : null },
        ]}
      />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => { if (!pending) setRemoving(null); }}
        title={removing ? `Delete scope ${removing.name}?` : ""}
        description="Deployments already recorded there keep the name; nothing in the cloud changes."
        confirmLabel="Delete scope"
        danger
        pending={pending}
        onConfirm={() => start(async () => {
          if (!removing) return;
          const r = await deleteScope(projectId, appId, removing.name);
          if (!r.ok) { setError(r.error); return; }
          setRemoving(null);
          router.refresh();
        })}
      >
        {error && <div role="alert" className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </ConfirmDialog>
    </>
  );
}
