"use client";

import { Check, Info } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Cell } from "@/components/ui/data-table";
import { Select } from "@/components/ui/select";
import { TBody, Table, Td, Th, Tr } from "@/components/ui/table";
import type { AccessCatalog } from "@/lib/permissions";

export function RolesCard({ access }: { access: AccessCatalog }) {
  const roles = access.roles;
  const [viewing, setViewing] = useState(roles[0]?.id ?? "");
  const role = roles.find((r) => r.id === viewing) ?? roles[0];
  return (
    <Panel>
      <PanelHeader title={<>Roles and permissions <Info className="size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-label="Roles are assigned per member under Members" /></>} description="Define what each role can do within this workspace." aside={<Badge className="h-6 shrink-0 px-2.5">{roles.length} roles</Badge>} />
      <div className="lg:hidden">
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
                  <div className="truncate font-mono text-[13px]">{p.id}</div>
                  <div className="mt-0.5 truncate text-[13px] text-secondary">{p.description}</div>
                </div>
                {allowed ? <Check aria-label="allowed" className="mt-0.5 size-4 shrink-0" strokeWidth={2.5} /> : <span aria-label="not allowed" className="mt-0.5 shrink-0 text-muted-foreground">—</span>}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="hidden lg:block">
        <Table columns={[{ width: 100 - 12 * roles.length }, ...roles.map(() => ({ width: 12 }))]}>
          <thead>
            <tr>
              <Th>Permission</Th>
              {roles.map((r) => <Th key={r.id} align="center" title={r.description}>{r.label}</Th>)}
            </tr>
          </thead>
          <TBody>
            {access.permissions.map((p) => (
              <Tr key={p.id}>
                <Td>
                  <Cell title={`${p.id} — ${p.description}`}><span className="font-mono text-[13px]">{p.id}</span> <span className="text-[13px] text-secondary">{p.description}</span></Cell>
                </Td>
                {roles.map((r) => (
                  <Td key={r.id} align="center">
                    {r.permissions.includes(p.id) ? <Check aria-label="allowed" className="mx-auto size-4" strokeWidth={2.5} /> : <span aria-label="not allowed" className="text-muted-foreground">—</span>}
                  </Td>
                ))}
              </Tr>
            ))}
          </TBody>
        </Table>
      </div>
    </Panel>
  );
}
