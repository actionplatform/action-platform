"use client";

import { ShieldCheck } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable } from "@/components/ui/data-table";
import { pageQuery, paginate } from "@/lib/page";
import type { AccessChange } from "@/lib/v1";

const TONE = { planned: "neutral", applied: "success", refused: "danger", failed: "danger" } as const;

export function ChangeTable({ title, changes, pageKey }: { title: string; changes: AccessChange[]; pageKey: string }) {
  const params = useSearchParams();
  const page = paginate(changes, pageQuery(Object.fromEntries(params.entries()), pageKey));

  return (
    <DataTable
      title={title}
      rows={page.items}
      paging={page}
      pageKey={pageKey}
      rowKey={(c) => `${c.service}:${c.account}:${c.resource}:${c.action}:${c.level}`}
      noun={["change", "changes"]}
      rowClassName={(c) => (c.status === "refused" ? "bg-status-bad/5" : undefined)}
      empty={{ icon: ShieldCheck, title: "No changes" }}
      columns={[
        { key: "action", label: "Change", width: 12, render: (c) => <Cell className="capitalize">{c.action}</Cell> },
        { key: "account", label: "Account", width: 22, render: (c) => <Cell mono>{c.account}</Cell> },
        { key: "resource", label: "Resource", width: 26, render: (c) => <Cell mono>{c.service}/{c.resource}</Cell> },
        { key: "level", label: "Level", width: 14, render: (c) => <Cell mono>{c.previous ? `${c.previous} → ${c.level}` : c.level}</Cell> },
        {
          key: "status",
          label: "Status",
          width: 26,
          render: (c) => (
            <Cell title={c.detail ? `${c.status}: ${c.detail}` : c.status}>
              <Badge tone={TONE[c.status]}>{c.status}</Badge>
              {c.detail && <span className={c.status === "refused" || c.status === "failed" ? "ml-2 text-status-bad" : "ml-2 text-secondary"}>{c.detail}</span>}
            </Cell>
          ),
        },
      ]}
    />
  );
}
