import { Check, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { can, PERMISSION_INFO, PERMISSIONS, ROLE_INFO, ROLES } from "@/lib/permissions";

export function RolesCard() {
  return (
    <Card className="rounded-[11px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-6 py-5">
        <div>
          <h2 className="flex items-center gap-2 text-[15px] font-semibold">Roles and permissions <Info className="size-3.5 text-muted-foreground" strokeWidth={1.75} aria-label="Roles are assigned per member under Members" /></h2>
          <p className="mt-1 text-[13px] text-secondary">Define what each role can do within this workspace.</p>
        </div>
        <Badge className="h-6 shrink-0 px-2.5">{ROLES.length} roles</Badge>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="bg-background/60 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-6 py-2.5 font-medium">Permission</th>
              {ROLES.map((r) => <th key={r} className="w-[110px] px-3 py-2.5 text-center font-medium" title={ROLE_INFO[r].description}>{ROLE_INFO[r].label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
            {PERMISSIONS.map((p) => (
              <tr key={p} className="transition-colors hover:bg-surface-hover/60">
                <td className="px-6 py-3.5">
                  <div className="font-mono text-[13px]">{p}</div>
                  <div className="mt-0.5 text-[13px] text-secondary">{PERMISSION_INFO[p]}</div>
                </td>
                {ROLES.map((r) => (
                  <td key={r} className="px-3 py-3.5 text-center">
                    {can(r, p) ? <Check aria-label="allowed" className="mx-auto size-4" strokeWidth={2.5} /> : <span aria-label="not allowed" className="text-muted-foreground">—</span>}
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
