"use client";

import { ArrowUpDown, ChevronDown, Search } from "lucide-react";
import { useId } from "react";
import { Menu } from "@/components/ui/menu";

export const SORTS = [
  { id: "updated-desc", label: "Updated recently" },
  { id: "updated-asc", label: "Oldest updated" },
  { id: "name-asc", label: "Name A–Z" },
  { id: "name-desc", label: "Name Z–A" },
] as const;

export type SortId = (typeof SORTS)[number]["id"];

export function ProjectsToolbar({ query, onQuery, sort, onSort }: { query: string; onQuery: (q: string) => void; sort: SortId; onSort: (s: SortId) => void }) {
  const id = useId();
  const current = SORTS.find((s) => s.id === sort)!;

  return (
    <div className="mt-7 mb-6 flex flex-col gap-3 md:flex-row md:items-center">
      <label htmlFor={id} className="relative block w-full max-w-[640px]">
        <span className="sr-only">Search projects</span>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.75} />
        <input
          id={id}
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search projects..."
          className="h-11 w-full rounded-lg border border-[#2a2a2a] bg-[#101010] pl-10 pr-3.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#525252] focus:outline-none focus:ring-2 focus:ring-white/[0.06]"
        />
      </label>

      <div className="md:ml-auto">
        <Menu
          label="Sort projects"
          items={SORTS.map((s) => ({ label: s.label, onSelect: () => onSort(s.id) }))}
          trigger={({ open, toggle, id: menuId }) => (
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={open}
              aria-controls={menuId}
              onClick={toggle}
              className="flex h-11 w-full items-center gap-2.5 rounded-lg border border-[#2a2a2a] bg-[#101010] px-3.5 text-sm text-foreground hover:border-border-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/[0.06] md:w-auto md:min-w-48"
            >
              <ArrowUpDown className="size-4 text-secondary" strokeWidth={1.75} />
              <span className="flex-1 text-left">{current.label}</span>
              <ChevronDown className="size-4 text-secondary" strokeWidth={1.75} />
            </button>
          )}
        />
      </div>
    </div>
  );
}
