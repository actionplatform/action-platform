"use client";

import { Check, Info } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import type { AccessCatalog } from "@/lib/permissions";

export function RolesCard({ access }: { access: AccessCatalog }) {
  const roles = access.roles;
  const [viewing, setViewing] = useState(roles[0]?.id ?? "");
  const role = roles.find((r) => r.id === viewing) ?? roles[0];
  return (
    <Card className="rounded-[11px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-4 md:px-6 md:py-5">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold">Roles and permissions <Info className="size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-label="Roles are assigned per member under Members" /></h2>
          <p className="mt-1 text-[13px] text-secondary">Define what each role can do within this workspace.</p>
        </div>
        <Badge className="h-6 shrink-0 px-2.5">{roles.length} roles</Badge>
      </header>
      <div className="md:hidden">
        <div className="border-b border-border-subtle px-4 py-3">
          <label className="block">
            <span className="mb-1 block text-xs text-secondary">Viewing role</span>
            <Select size="lg" aria-label="Viewing role" value={viewing} onChange={setViewing} options={roles.map((r) => ({ value: r.id, label: r.label }))} />
          </label>
          {role?.description && <p className="mt-2 text-[13px] text-secondary">{role.description}</p>}
        </div>
        <ul className="divide-y divide-border-subtle">
          {access.permissions.map((p) => {
            const allowed = !!role?.permissions.includes(p.id);
            return (
              <li key={p.id} className="flex items-start gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-[13px]">{p.id}</div>
                  <div className="mt-0.5 text-[13px] text-secondary">{p.description}</div>
                </div>
                {allowed ? <Check aria-label="allowed" className="mt-0.5 size-4 shrink-0" strokeWidth={2.5} /> : <span aria-label="not allowed" className="mt-0.5 shrink-0 text-muted-foreground">—</span>}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="bg-background/60 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-6 py-2.5 font-medium">Permission</th>
              {roles.map((r) => <th key={r.id} className="w-[110px] px-3 py-2.5 text-center font-medium" title={r.description}>{r.label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
            {access.permissions.map((p) => (
              <tr key={p.id} className="transition-colors hover:bg-surface-hover/60">
                <td className="px-6 py-3.5">
                  <div className="font-mono text-[13px]">{p.id}</div>
                  <div className="mt-0.5 text-[13px] text-secondary">{p.description}</div>
                </td>
                {roles.map((r) => (
                  <td key={r.id} className="px-3 py-3.5 text-center">
                    {r.permissions.includes(p.id) ? <Check aria-label="allowed" className="mx-auto size-4" strokeWidth={2.5} /> : <span aria-label="not allowed" className="text-muted-foreground">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
