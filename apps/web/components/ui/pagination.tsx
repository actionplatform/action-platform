"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { Button } from "./button";
import { Select } from "./select";

export const PER_PAGE = [10, 25, 50, 100] as const;

export function usePagination<T>(rows: T[], key = "") {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const pageKey = key ? `${key}_page` : "page";
  const perKey = key ? `${key}_per` : "per";
  const per = Math.max(1, Number(params.get(perKey)) || PER_PAGE[0]);
  const pages = Math.max(1, Math.ceil(rows.length / per));
  const page = Math.min(pages, Math.max(1, Number(params.get(pageKey)) || 1));
  const slice = useMemo(() => rows.slice((page - 1) * per, page * per), [rows, page, per]);

  const set = (next: { page?: number; per?: number }) => {
    const q = new URLSearchParams(params.toString());
    if (next.per !== undefined) { q.set(perKey, String(next.per)); q.set(pageKey, "1"); }
    if (next.page !== undefined) q.set(pageKey, String(next.page));
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  };

  return { rows: slice, page, pages, per, total: rows.length, setPage: (p: number) => set({ page: p }), setPer: (p: number) => set({ per: p }) };
}

type Props = { page: number; pages: number; per: number; total: number; onPage: (page: number) => void; onPer: (per: number) => void; noun?: [string, string] };

export function Pagination({ page, pages, per, total, onPage, onPer, noun = ["item", "items"] }: Props) {
  if (total === 0) return null;
  const from = (page - 1) * per + 1;
  const to = Math.min(total, page * per);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle px-4 py-2 text-[13px] text-secondary">
      <span>{from}–{to} of {total} {total === 1 ? noun[0] : noun[1]}</span>
      <div className="flex items-center gap-2">
        <Select size="sm" value={String(per)} onChange={(v) => onPer(Number(v))} aria-label="Items per page" options={PER_PAGE.map((n) => ({ value: String(n), label: `${n} per page` }))} className="w-32" />
        <Button size="icon" variant="ghost" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft className="size-4" strokeWidth={1.75} /></Button>
        <span className="tabular-nums">{page} / {pages}</span>
        <Button size="icon" variant="ghost" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}><ChevronRight className="size-4" strokeWidth={1.75} /></Button>
      </div>
    </div>
  );
}
