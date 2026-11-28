import Link from "next/link";
import type { EventKind } from "@/lib/insights";
import { cn } from "@/lib/utils";

export const ACTIVITY_FILTERS: { kind: EventKind | null; label: string }[] = [
  { kind: null, label: "All" },
  { kind: "release", label: "Releases" },
  { kind: "deployment", label: "Deployments" },
  { kind: "protection", label: "Branch protection" },
];

export function ActivityFilter({ base, current }: { base: string; current: EventKind | null }) {
  return (
    <nav aria-label="Filter activity" className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
      <ul className="flex gap-1.5">
        {ACTIVITY_FILTERS.map(({ kind, label }) => {
          const active = kind === current;
          return (
            <li key={label} className="shrink-0">
              <Link
                href={kind ? `${base}?kind=${kind}` : base}
                aria-current={active ? "page" : undefined}
                className={cn("flex h-8 items-center rounded-md border px-3 text-[13px] transition-colors", active ? "border-foreground bg-surface-selected text-foreground" : "border-border text-secondary hover:border-border-hover hover:text-foreground")}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
