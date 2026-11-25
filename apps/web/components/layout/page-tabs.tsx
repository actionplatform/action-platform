import Link from "next/link";
import { cn } from "@/lib/utils";

export type PageTab = { id: string; label: string };

export function pickTab(tabs: PageTab[], raw: string | string[] | undefined): string {
  const id = Array.isArray(raw) ? raw[0] : raw;
  return tabs.some((t) => t.id === id) ? (id as string) : tabs[0].id;
}

export function PageTabs({ label, tabs, active }: { label: string; tabs: PageTab[]; active: string }) {
  return (
    <nav aria-label={label} className="mb-5 border-b border-border">
      <ul role="tablist" className="flex gap-1">
        {tabs.map(({ id, label: text }) => (
          <li key={id} role="presentation" className="shrink-0">
            <Link
              href={`?tab=${id}`}
              scroll={false}
              role="tab"
              aria-selected={id === active}
              className={cn("-mb-px flex h-11 items-center border-b-2 px-3 text-sm", id === active ? "border-foreground text-foreground" : "border-transparent text-secondary hover:text-foreground")}
            >
              {text}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
