import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn("overflow-hidden rounded-lg border border-border bg-surface", className)} {...props} />;
}

export function PanelHeader({ title, aside, className }: { title: string; aside?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex h-12 items-center justify-between gap-3 border-b border-border px-4", className)}>
      <h2 className="text-sm font-semibold">{title}</h2>
      {aside}
    </header>
  );
}

export function PanelBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4", className)} {...props} />;
}
