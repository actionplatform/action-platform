"use client";

import { ChevronDown, Code2, LayoutGrid, List, Search } from "lucide-react";
import { useId } from "react";
import { Menu } from "@/components/ui/menu";
import { cn } from "@/lib/utils";

export type TemplateView = "grid" | "list";

const field = "h-11 rounded-lg border border-[#2a2a2a] bg-[#101010] text-sm text-foreground";

export function TemplatesToolbar({ search, onSearch, language, languages, onLanguage, view, onView }: {
  search: string;
  onSearch: (v: string) => void;
  language: string;
  languages: { id: string; label: string }[];
  onLanguage: (id: string) => void;
  view: TemplateView;
  onView: (v: TemplateView) => void;
}) {
  const id = useId();
  const current = languages.find((l) => l.id === language)?.label ?? "All languages";

  return (
    <div className="mt-[26px] flex flex-col gap-3 md:flex-row md:items-center">
      <label htmlFor={id} className="relative block flex-1">
        <span className="sr-only">Search templates</span>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-[17px] -translate-y-1/2 text-muted-foreground" strokeWidth={1.75} />
        <input
          id={id}
          type="search"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search templates..."
          className={cn(field, "w-full pl-10 pr-3.5 placeholder:text-muted-foreground focus:border-[#525252] focus:outline-none focus:ring-2 focus:ring-white/[0.06]")}
        />
      </label>

      <div className="flex gap-3">
        <Menu
          label="Filter by language"
          items={[{ id: "all", label: "All languages" }, ...languages].map((l) => ({ label: l.label, onSelect: () => onLanguage(l.id) }))}
          trigger={({ open, toggle, id: menuId }) => (
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={open}
              aria-controls={menuId}
              onClick={toggle}
              className={cn(field, "flex min-w-0 flex-1 items-center gap-2.5 px-3.5 hover:border-border-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/[0.06] md:min-w-[204px] md:flex-none")}
            >
              <Code2 className="size-4 text-secondary" strokeWidth={1.75} />
              <span className="flex-1 truncate text-left">{current}</span>
              <ChevronDown className="size-4 text-secondary" strokeWidth={1.75} />
            </button>
          )}
        />

        <div role="group" aria-label="View" className={cn(field, "flex overflow-hidden")}>
          {(["grid", "list"] as const).map((v) => {
            const Icon = v === "grid" ? LayoutGrid : List;
            return (
              <button
                key={v}
                type="button"
                aria-label={v === "grid" ? "Grid view" : "List view"}
                aria-pressed={view === v}
                onClick={() => onView(v)}
                className={cn("flex w-[42px] items-center justify-center transition-colors focus-visible:outline-none focus-visible:bg-surface-hover", view === v ? "bg-[#1b1b1b] text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <Icon className="size-[17px]" strokeWidth={1.75} />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
