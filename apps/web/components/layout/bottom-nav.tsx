"use client";

import { Building2, FolderGit2, LayoutTemplate, Plug, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const items = [
  { href: "/projects", label: "Projects", icon: FolderGit2 },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/organization", label: "Organization", icon: Building2 },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="md:hidden fixed inset-x-0 bottom-0 z-30 border-t border-border bg-sidebar pb-[env(safe-area-inset-bottom)]">
      <ul className="grid h-[76px] grid-cols-5">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href} className="min-w-0">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn("mx-1.5 my-1.5 flex h-[64px] flex-col items-center justify-center gap-1.5 rounded-[9px] text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground", active ? "bg-surface-selected text-foreground" : "text-secondary hover:text-foreground")}
              >
                <Icon className="size-5" strokeWidth={1.75} />
                <span className="truncate">{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
