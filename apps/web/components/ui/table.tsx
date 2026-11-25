import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type Align = "left" | "right" | "center";

export const TABLE_CLASS = {
  head: "h-9 px-3 first:pl-4 last:pr-4 text-left align-middle text-xs font-medium whitespace-nowrap text-secondary",
  cell: "px-3 py-2 first:pl-4 last:pr-4 align-middle",
  body: "divide-y divide-border-subtle border-t border-border-subtle",
  row: "transition-colors hover:bg-surface-hover/60",
} as const;

export function alignClass(align?: Align, numeric?: boolean): string | undefined {
  return cn((align === "right" || numeric) && "text-right", align === "center" && "text-center", numeric && "tabular-nums") || undefined;
}

type AlignProps = { align?: Align; numeric?: boolean };

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full text-sm", className)} {...props} />
    </div>
  );
}

export function TBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn(TABLE_CLASS.body, className)} {...props} />;
}

export function Tr({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn(TABLE_CLASS.row, className)} {...props} />;
}

export function Th({ className, align, numeric, ...props }: Omit<ThHTMLAttributes<HTMLTableCellElement>, "align"> & AlignProps) {
  return <th className={cn(TABLE_CLASS.head, alignClass(align, numeric), className)} {...props} />;
}

export function Td({ className, align, numeric, ...props }: Omit<TdHTMLAttributes<HTMLTableCellElement>, "align"> & AlignProps) {
  return <td className={cn(TABLE_CLASS.cell, alignClass(align, numeric), className)} {...props} />;
}
