"use client";

import type { LucideIcon } from "lucide-react";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "./button";
import { Select } from "./select";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

export const PER_PAGE = [10, 25, 50, 100] as const;

export const TABLE = { toolbar: 56, header: 40, row: 52, footer: 56, rows: 10, padding: 16, gap: 16, radius: 10 } as const;

export type Hide = "sm" | "md" | "lg" | "xl";
export type Column<T> = { key: string; label: string; width: number; align?: "left" | "right"; hide?: Hide; render: (row: T, index: number) => ReactNode };

const HIDE: Record<Hide, string> = { sm: "hidden sm:table-cell", md: "hidden md:table-cell", lg: "hidden lg:table-cell", xl: "hidden xl:table-cell" };

export type PageState = { total: number; page: number; per: number };

type Props<T> = {
  title: string;
  rows: T[];
  paging: PageState;
  rowKey: (row: T) => string;
  columns: Column<T>[];
  noun: [string, string];
  meta?: ReactNode;
  action?: ReactNode;
  newHref?: string | null;
  newLabel?: string;
  empty: { icon: LucideIcon; title: string; text?: ReactNode };
  pageKey?: string;
  minWidth?: number;
  rowClassName?: (row: T) => string | undefined;
};

export function NewLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 text-sm font-medium hover:border-border-hover hover:bg-surface-hover"><Plus className="size-3.5" strokeWidth={2} /> {label}</Link>;
}

export function Cell({ children, className, mono, muted, title }: { children: ReactNode; className?: string; mono?: boolean; muted?: boolean; title?: string }) {
  return <span title={title} className={cn("block min-w-0 truncate", mono && "font-mono text-[13px]", muted && "text-secondary", className)}>{children}</span>;
}

export function Inline({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("flex min-w-0 items-center gap-2 whitespace-nowrap", className)}>{children}</span>;
}

function usePageNav(key = "") {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const pageKey = key ? `${key}_page` : "page";
  const perKey = key ? `${key}_per` : "per";
  return (next: { page?: number; per?: number }) => {
    const q = new URLSearchParams(params.toString());
    if (next.per !== undefined) { q.set(perKey, String(next.per)); q.set(pageKey, "1"); }
    if (next.page !== undefined) q.set(pageKey, String(next.page));
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  };
}

export function DataTable<T>({ title, rows, paging, rowKey, columns, noun, meta, action, newHref, newLabel = "New", empty, pageKey, minWidth = 720, rowClassName }: Props<T>) {
  const nav = usePageNav(pageKey);
  const pages = Math.max(1, Math.ceil(paging.total / paging.per));
  const offset = (paging.page - 1) * paging.per;
  const slots = Math.max(0, paging.per - rows.length);
  const from = paging.total === 0 ? 0 : offset + 1;
  const to = Math.min(paging.total, offset + rows.length);
  const cell = "px-2 first:pl-4 last:pr-4";
  const Icon = empty.icon;

  return (
    <section className="overflow-hidden border border-border bg-surface" style={{ borderRadius: TABLE.radius }}>
      <header className="flex items-center justify-between gap-4 border-b border-border px-4" style={{ height: TABLE.toolbar }}>
        <div className="flex min-w-0 items-baseline gap-3">
          <h2 className="truncate text-sm font-semibold">{title}</h2>
          <span className="hidden truncate text-[13px] text-secondary sm:block">{paging.total} {paging.total === 1 ? noun[0] : noun[1]}{meta && <> · {meta}</>}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {action}
          {newHref && <NewLink href={newHref} label={newLabel} />}
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full table-fixed text-sm" style={{ minWidth }}>
          <colgroup>{columns.map((c) => <col key={c.key} className={c.hide ? HIDE[c.hide].replace("table-cell", "table-column") : undefined} style={{ width: `${c.width}%` }} />)}</colgroup>
          <thead>
            <tr style={{ height: TABLE.header }}>
              {columns.map((c) => <th key={c.key} className={cn(cell, "whitespace-nowrap text-left text-xs font-medium text-muted-foreground", c.align === "right" && "text-right", c.hide && HIDE[c.hide])}>{c.label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
            {paging.total === 0 && (
              <tr style={{ height: TABLE.row * TABLE.rows }}>
                <td colSpan={columns.length} className="px-4 text-center align-middle">
                  <Icon className="mx-auto size-5 text-secondary" strokeWidth={1.5} />
                  <div className="mt-3 text-sm font-medium">{empty.title}</div>
                  {empty.text && <div className="mx-auto mt-0.5 max-w-md text-[13px] text-secondary">{empty.text}</div>}
                </td>
              </tr>
            )}
            {rows.map((row, i) => (
              <tr key={rowKey(row)} className={cn("align-middle", rowClassName?.(row))} style={{ height: TABLE.row, minHeight: TABLE.row, maxHeight: TABLE.row }}>
                {columns.map((c) => <td key={c.key} className={cn(cell, "overflow-hidden whitespace-nowrap align-middle", c.align === "right" && "text-right", c.hide && HIDE[c.hide])}>{c.render(row, offset + i)}</td>)}
              </tr>
            ))}
            {paging.total > 0 && Array.from({ length: slots }).map((_, i) => (
              <tr key={`slot-${i}`} aria-hidden style={{ height: TABLE.row }}><td colSpan={columns.length} /></tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between gap-4 border-t border-border px-4 text-[13px] text-secondary" style={{ height: TABLE.footer }}>
        <span className="truncate">{from}–{to} of {paging.total} {paging.total === 1 ? noun[0] : noun[1]}</span>
        <div className="flex shrink-0 items-center gap-2">
          <Select size="sm" value={String(paging.per)} onChange={(v) => nav({ per: Number(v) })} aria-label="Items per page" options={PER_PAGE.map((n) => ({ value: String(n), label: `${n} per page` }))} className="w-32" />
          <Button size="icon" variant="ghost" aria-label="Previous page" disabled={paging.page <= 1} onClick={() => nav({ page: paging.page - 1 })}><ChevronLeft className="size-4" strokeWidth={1.75} /></Button>
          <span className="tabular-nums">{paging.page} / {pages}</span>
          <Button size="icon" variant="ghost" aria-label="Next page" disabled={paging.page >= pages} onClick={() => nav({ page: paging.page + 1 })}><ChevronRight className="size-4" strokeWidth={1.75} /></Button>
        </div>
      </footer>
    </section>
  );
}
