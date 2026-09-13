import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn("overflow-hidden rounded-lg border border-border bg-surface", className)} {...props} />;
}

export function PanelHeader({ title, aside, className }: { title: string; aside?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-border px-4 py-2", className)}>
      <h2 className="text-sm font-semibold">{title}</h2>
      {aside}
    </header>
  );
}

export function PanelBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4", className)} {...props} />;
}
