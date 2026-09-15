"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/settings/people", label: "Members", exact: true },
  { href: "/settings/people/teams", label: "Teams" },
];

export function PeopleTabs() {
  const pathname = usePathname();

  return (
    <nav aria-label="People" className="mb-5 flex gap-1 border-b border-border">
      {TABS.map(({ href, label, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn("-mb-px flex h-10 items-center border-b-2 px-3 text-sm", active ? "border-foreground text-foreground" : "border-transparent text-secondary hover:text-foreground")}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
