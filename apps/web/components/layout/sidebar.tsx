"use client";

import { Boxes, FolderGit2, LayoutTemplate, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { UserMenu } from "./user-menu";

const items = [
  { href: "/projects", label: "Projects", icon: FolderGit2 },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ version, user }: { version: string; user: { name: string; email: string } }) {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card flex flex-col">
      <div className="flex items-center gap-2 px-4 h-14 border-b border-border">
        <Boxes className="size-5" />
        <span className="font-semibold text-sm">action-platform</span>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                active ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <UserMenu name={user.name} email={user.email} />
      <div className="px-4 py-2 text-xs text-muted-foreground border-t border-border">v{version}</div>
    </aside>
  );
}
