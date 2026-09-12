"use client";

import { Boxes, FolderGit2, LayoutTemplate, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Org } from "@/lib/types";
import { cn } from "@/lib/utils";
import { OrgSwitcher } from "./org-switcher";
import { UserMenu } from "./user-menu";

const items = [
  { href: "/projects", label: "Projects", icon: FolderGit2 },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/settings", label: "Settings", icon: Settings },
];

type Props = { version: string; user: { name: string; email: string }; org: Org; orgs: Org[] };

export function Sidebar({ version, user, org, orgs }: Props) {
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <>
      <aside className="hidden md:flex w-56 shrink-0 border-r border-border bg-sidebar flex-col sticky top-0 h-screen">
        <div className="flex items-center gap-2 px-4 h-14 border-b border-border">
          <Boxes className="size-5" />
          <span className="font-semibold text-sm">action-platform</span>
        </div>
        <div className="p-2 border-b border-border">
          <OrgSwitcher org={org} orgs={orgs} />
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive(href) ? "bg-surface-hover text-foreground font-medium" : "text-secondary hover:bg-surface-hover hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>
        <UserMenu name={user.name} email={user.email} />
        <div className="px-4 py-2 text-xs text-muted-foreground border-t border-border">v{version}</div>
      </aside>

      <header className="md:hidden sticky top-0 z-10 flex items-center justify-between h-12 px-3 border-b border-border bg-sidebar">
        <div className="flex items-center gap-2 text-sm font-semibold min-w-0"><Boxes className="size-4 shrink-0" /> <span className="truncate">{org.name}</span></div>
        <nav className="flex gap-1">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "flex size-8 items-center justify-center rounded-md",
                isActive(href) ? "bg-surface-hover text-foreground" : "text-secondary hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
            </Link>
          ))}
        </nav>
      </header>
    </>
  );
}
