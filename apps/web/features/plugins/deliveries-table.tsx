"use client";

import { Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import { relativeTime } from "@/lib/time";

export type Delivery = {
  id: string;
  event: string;
  route: string;
  project: string;
  app: string;
  url?: string | null;
  status: string;
  attempts: number;
  error?: string | null;
  created_at?: string | null;
  finished_at?: string | null;
};

const STATUS: Record<string, { label: string; tone: "success" | "warning" | "danger" | "neutral" }> = {
  done: { label: "Delivered", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  running: { label: "Sending", tone: "neutral" },
  queued: { label: "Queued", tone: "warning" },
};

export function DeliveriesTable({ rows }: { rows: Delivery[] }) {
  return (
    <DataTable
      title="Deliveries"
      rows={rows}
      rowKey={(r) => r.id}
      noun={["delivery", "deliveries"]}
      empty={{ icon: Send, title: "No deliveries yet", text: "Events appear here once the plugin's options route one somewhere." }}
      minWidth={760}
      columns={[
        { key: "event", label: "Event", width: 22, render: (r) => r.url ? <a href={r.url} className="block truncate font-mono text-[13px] hover:underline underline-offset-4">{r.event}</a> : <Cell mono>{r.event}</Cell> },
        { key: "route", label: "To", width: 12, render: (r) => <Cell>{r.route}</Cell> },
        { key: "app", label: "App", width: 20, hide: "sm", render: (r) => <Cell muted title={`${r.project}/${r.app}`}>{r.project}/{r.app}</Cell> },
        { key: "status", label: "Status", width: 26, render: (r) => { const s = STATUS[r.status] ?? { label: r.status, tone: "neutral" as const }; return <Inline><Badge tone={s.tone} className="shrink-0">{s.label}</Badge>{r.attempts > 1 && <span className="text-xs text-secondary">{r.attempts} attempts</span>}{r.error && <Cell muted title={r.error}>{r.error}</Cell>}</Inline>; } },
        { key: "when", label: "When", width: 14, hide: "sm", render: (r) => <Cell muted>{r.created_at ? relativeTime(r.created_at) : "—"}</Cell> },
      ]}
    />
  );
}
