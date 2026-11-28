import { CircleAlert, CircleCheck, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { AccessAudit, ServiceAuditRow } from "@/lib/v1";
import { ChangeTable } from "./change-table";
import { needsConnection } from "./plan";

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <div className="text-xs text-secondary">{title} ({items.length})</div>
      <ul className="mt-1 flex flex-wrap gap-1.5">
        {items.map((item) => <li key={item}><Badge className="font-mono">{item}</Badge></li>)}
      </ul>
    </div>
  );
}

function ServiceCard({ row }: { row: ServiceAuditRow }) {
  const drift = row.drift ?? [];
  const levels = Object.entries(row.levels ?? {});
  return (
    <Panel>
      <PanelHeader
        title={<>{row.ok ? <CircleCheck className="size-4 text-status-ok" strokeWidth={1.75} aria-label="Readable" /> : <CircleAlert className="size-4 text-status-bad" strokeWidth={1.75} aria-label="Failed" />}<span className="font-mono">{row.service}</span></>}
        aside={<div className="flex items-center gap-2">{row.ok && !row.imported && <Badge tone="warning">Not imported</Badge>}{row.ok && <Badge>{row.live} live{row.imported ? ` / ${row.wanted} wanted` : ""}</Badge>}</div>}
      />
      <div className="space-y-4 p-4 text-[13px]">
        {row.error && (
          <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-status-bad">
            <p className="whitespace-pre-wrap break-words">{row.error}</p>
            {needsConnection(row.error) && <Link href="/connect/git" className="mt-1 inline-block font-medium underline">Open Git to connect it</Link>}
          </div>
        )}
        {row.ok && !row.imported && <p className="text-secondary">Not imported yet: no drift is reported until a sync imports what this service holds today.</p>}
        {levels.length > 0 && (
          <div>
            <div className="text-xs text-secondary">Levels per resource kind</div>
            <dl className="mt-1 space-y-1">
              {levels.map(([kind, list]) => (
                <div key={kind} className="flex flex-wrap items-baseline gap-x-2"><dt className="font-mono">{kind}</dt><dd className="font-mono text-secondary">{list.join(" < ")}</dd></div>
              ))}
            </dl>
          </div>
        )}
        <List title="Members without an account" items={row.members_without_account ?? []} />
        <List title="Outside accounts" items={row.outside_accounts ?? []} />
      </div>
      {drift.length > 0 && (
        <div className="border-t border-border">
          <div className="px-4 pt-3 text-xs text-secondary">Drift: what a sync would change ({drift.length})</div>
          <ChangeTable changes={drift} />
        </div>
      )}
      {row.ok && row.imported && drift.length === 0 && <div className="border-t border-border px-4 py-3 text-[13px] text-secondary">No drift.</div>}
    </Panel>
  );
}

export function ServiceAudits({ audit }: { audit: AccessAudit }) {
  if (audit.services.length === 0) {
    return (
      <Panel>
        <EmptyState icon={ShieldCheck} title="No service to manage" text="Connect GitHub under Settings → Git, or configure a plugin that manages access under Plugins." />
      </Panel>
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-[13px] text-secondary">{audit.organization_members} organization {audit.organization_members === 1 ? "member" : "members"}. Read from each service on every load.</p>
      {audit.services.map((row) => <ServiceCard key={row.service} row={row} />)}
    </div>
  );
}
