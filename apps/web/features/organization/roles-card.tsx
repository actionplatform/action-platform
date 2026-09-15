import { Check, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { AccessCatalog } from "@/lib/permissions";

export function RolesCard({ access }: { access: AccessCatalog }) {
  const roles = access.roles;
  return (
    <Card className="rounded-[11px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-6 py-5">
        <div>
          <h2 className="flex items-center gap-2 text-[15px] font-semibold">Roles and permissions <Info className="size-3.5 text-muted-foreground" strokeWidth={1.75} aria-label="Roles are assigned per member under Members" /></h2>
          <p className="mt-1 text-[13px] text-secondary">Define what each role can do within this workspace.</p>
        </div>
        <Badge className="h-6 shrink-0 px-2.5">{roles.length} roles</Badge>
      </header>
      <div className="overflow-x-auto">
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
