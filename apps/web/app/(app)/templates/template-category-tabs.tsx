"use client";

import { cn } from "@/lib/utils";

export function TemplateCategoryTabs({ tabs, active, onChange }: { tabs: { id: string; label: string; count: number }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div role="tablist" aria-label="Template categories" className="mt-4 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {tabs.map((t) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(t.id)}
            className={cn(
              "flex h-[38px] shrink-0 items-center gap-2 rounded-[7px] border px-3.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground",
              selected ? "border-foreground bg-foreground text-primary-foreground" : "border-border text-secondary hover:border-border-hover hover:text-foreground",
            )}
          >
            {t.label}
            <span className={cn("rounded-full px-1.5 text-xs tabular-nums", selected ? "bg-black/10 text-primary-foreground" : "bg-surface-hover text-muted-foreground")}>{t.count}</span>
          </button>
        );
      })}
    </div>
  );
}
