import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type Align = "left" | "right" | "center";
export type Hide = "sm" | "md" | "lg" | "xl";

export const HIDE_BELOW: Record<Hide, string> = { sm: "hidden sm:table-cell", md: "hidden md:table-cell", lg: "hidden lg:table-cell", xl: "hidden xl:table-cell" };
export const HIDE_COL_BELOW: Record<Hide, string> = { sm: "hidden sm:table-column", md: "hidden md:table-column", lg: "hidden lg:table-column", xl: "hidden xl:table-column" };

export const TABLE_CLASS = {
  head: "h-9 px-3 first:pl-4 last:pr-4 text-left align-middle text-xs font-medium whitespace-nowrap text-secondary",
  cell: "overflow-hidden px-3 py-2 align-middle whitespace-nowrap first:pl-4 last:pr-4",
  body: "divide-y divide-border-subtle border-t border-border-subtle",
  row: "transition-colors hover:bg-surface-hover/60",
} as const;

export function alignClass(align?: Align, numeric?: boolean): string | undefined {
  return cn((align === "right" || numeric) && "text-right", align === "center" && "text-center", numeric && "tabular-nums") || undefined;
}

type AlignProps = { align?: Align; numeric?: boolean; hideBelow?: Hide };

export type TableColumn = { width: number | string; hideBelow?: Hide };

export function widthOf(width: number | string): string {
  return typeof width === "number" ? `${width}%` : width;
}

export function Table({ className, columns, children, ...props }: HTMLAttributes<HTMLTableElement> & { columns: TableColumn[] }) {
  return (
    <table className={cn("w-full table-fixed text-sm", className)} {...props}>
      <colgroup>{columns.map((c, i) => <col key={i} className={c.hideBelow ? HIDE_COL_BELOW[c.hideBelow] : undefined} style={{ width: widthOf(c.width) }} />)}</colgroup>
      {children}
    </table>
  );
}

export function TBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn(TABLE_CLASS.body, className)} {...props} />;
}

export function Tr({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn(TABLE_CLASS.row, className)} {...props} />;
}

export function Th({ className, align, numeric, hideBelow, ...props }: Omit<ThHTMLAttributes<HTMLTableCellElement>, "align"> & AlignProps) {
  return <th className={cn(TABLE_CLASS.head, "overflow-hidden text-ellipsis", alignClass(align, numeric), hideBelow && HIDE_BELOW[hideBelow], className)} {...props} />;
}

export function Td({ className, align, numeric, hideBelow, ...props }: Omit<TdHTMLAttributes<HTMLTableCellElement>, "align"> & AlignProps) {
  return <td className={cn(TABLE_CLASS.cell, alignClass(align, numeric), hideBelow && HIDE_BELOW[hideBelow], className)} {...props} />;
}
