"use client";

import type { LucideIcon } from "lucide-react";
import { Plus } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { EmptyState } from "./empty-state";
import { Pagination, usePagination } from "./pagination";
import { Panel, PanelHeader } from "./panel";
import { cn } from "@/lib/utils";

export type Column<T> = { key: string; label: string; className?: string; render: (row: T, index: number) => ReactNode };

type Props<T> = {
  title: string;
  rows: T[];
  rowKey: (row: T) => string;
  columns: Column<T>[];
  card: (row: T, index: number) => ReactNode;
  noun: [string, string];
  meta?: ReactNode;
  action?: ReactNode;
  newHref?: string | null;
  newLabel?: string;
  empty: { icon: LucideIcon; title: string; text?: ReactNode };
  pageKey?: string;
  rowClassName?: (row: T) => string | undefined;
  after?: (row: T, index: number) => ReactNode;
  minWidth?: string;
};

export function NewLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-medium hover:border-border-hover hover:bg-surface-hover"><Plus className="size-3.5" strokeWidth={2} /> {label}</Link>;
}

export function DataList<T>({ title, rows: all, rowKey, columns, card, noun, meta, action, newHref, newLabel = "New", empty, pageKey, rowClassName, after, minWidth = "640px" }: Props<T>) {
  const paging = usePagination(all, pageKey);
  const offset = (paging.page - 1) * paging.per;

  return (
    <Panel>
      <PanelHeader
        title={title}
        aside={
          <div className="flex items-center gap-3">
            <span className="hidden text-[13px] text-secondary sm:block">{all.length} {all.length === 1 ? noun[0] : noun[1]}{meta && <> · {meta}</>}</span>
            {action}
            {newHref && <NewLink href={newHref} label={newLabel} />}
          </div>
        }
      />
      {all.length === 0 ? (
        <EmptyState icon={empty.icon} title={empty.title} text={empty.text} />
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm" style={{ minWidth }}>
              <thead><tr className="text-left text-xs text-muted-foreground">{columns.map((c) => <th key={c.key} className={cn("py-2 pr-4 font-medium first:px-4 last:pr-3", c.className)}>{c.label}</th>)}</tr></thead>
              <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
                {paging.rows.map((row, i) => [
                  <tr key={rowKey(row)} className={cn("align-middle", rowClassName?.(row))}>{columns.map((c) => <td key={c.key} className={cn("py-2.5 pr-4 first:px-4 last:pr-3", c.className)}>{c.render(row, offset + i)}</td>)}</tr>,
                  after?.(row, offset + i),
                ])}
              </tbody>
            </table>
          </div>
          <ul className="divide-y divide-border-subtle border-t border-border-subtle md:hidden">
            {paging.rows.map((row, i) => <li key={rowKey(row)} className="px-4 py-3 text-sm">{card(row, offset + i)}</li>)}
          </ul>
          <Pagination page={paging.page} pages={paging.pages} per={paging.per} total={paging.total} onPage={paging.setPage} onPer={paging.setPer} noun={noun} />
        </>
      )}
    </Panel>
  );
}
