"use client";

import { Activity, ArrowLeft, Users, FolderGit2, LayoutDashboard, LayoutTemplate, Menu, Rocket, Settings, SlidersHorizontal, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/logo";
import type { Org } from "@/lib/types";
import { cn } from "@/lib/utils";
import { OrgSwitcher } from "./org-switcher";
import { useScope } from "./scope";
import { UserMenu } from "./user-menu";

const items = [
  { href: "/projects", label: "Projects", icon: FolderGit2 },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/teams", label: "Teams", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

const appItems = [
  { tab: "", label: "Overview", icon: LayoutDashboard },
  { tab: "activity", label: "Activity", icon: Activity },
  { tab: "releases", label: "Releases", icon: Rocket },
  { tab: "configuration", label: "Configuration", icon: SlidersHorizontal },
  { tab: "settings", label: "Settings", icon: Settings },
];

const link = "mx-2.5 my-1 flex h-11 items-center gap-3 rounded-[7px] px-3.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground";

type Props = { versions: { web: string; api: string; lib: string }; user: { name: string; email: string }; org: Org; orgs: Org[] };

export function Sidebar({ versions, user, org, orgs }: Props) {
  const pathname = usePathname();
  const { scope } = useScope();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const panel = (
    <div className="flex h-full flex-col">
      <div className="flex h-[66px] items-center gap-2.5 border-b border-border px-5">
        <Logo className="size-5" />
        <span className="text-[15px] font-semibold">action-platform</span>
        <button type="button" aria-label="Close navigation" onClick={() => setOpen(false)} className="ml-auto text-secondary hover:text-foreground lg:hidden"><X className="size-4" /></button>
      </div>
      <div className="border-b border-border px-3 py-3">
        <OrgSwitcher org={org} orgs={orgs} />
      </div>
      {scope ? (
        <nav aria-label={scope.appName} className="flex-1 py-2">
          <Link href={`/projects/${scope.projectId}`} className={cn(link, "text-secondary hover:bg-surface-hover hover:text-foreground")}>
            <ArrowLeft className="size-[18px]" strokeWidth={1.75} />
            <span className="truncate">{scope.projectName}</span>
          </Link>
          <div className="mx-5 mb-1 mt-3 truncate font-mono text-xs text-muted-foreground">{scope.appName}</div>
          {appItems.map(({ tab, label, icon: Icon }) => {
            const base = `/projects/${scope.projectId}/apps/${scope.appId}`;
            const href = tab ? `${base}/${tab}` : base;
            const active = tab ? pathname.startsWith(href) : pathname === base;
            return (
              <Link
                key={label}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(link, active ? "bg-surface-selected text-foreground" : "text-secondary hover:bg-surface-hover hover:text-foreground")}
              >
                <Icon className="size-[18px]" strokeWidth={1.75} />
                {label}
              </Link>
            );
          })}
        </nav>
      ) : (
        <nav aria-label="Main" className="flex-1 py-2">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={isActive(href) ? "page" : undefined}
              className={cn(link, isActive(href) ? "bg-surface-selected text-foreground" : "text-secondary hover:bg-surface-hover hover:text-foreground")}
            >
              <Icon className="size-[18px]" strokeWidth={1.75} />
              {label}
            </Link>
          ))}
        </nav>
      )}
      <UserMenu name={user.name} email={user.email} />
      <div className="flex flex-wrap gap-x-3 border-t border-border-subtle px-5 py-2.5 font-mono text-[11px] text-muted-foreground">
        <span>web {versions.web}</span>
        <span>api {versions.api}</span>
        <span>lib {versions.lib}</span>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden lg:block fixed inset-y-0 left-0 w-[280px] border-r border-border bg-sidebar">{panel}</aside>

      <header className="lg:hidden sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-sidebar px-4">
        <button type="button" aria-label="Open navigation" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(true)} className="flex size-10 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground">
          <Menu className="size-5" />
        </button>
        <Logo className="size-4" />
        <span className="truncate text-sm font-semibold">{org.name}</span>
      </header>

      {open && (
        <div className="lg:hidden fixed inset-0 z-40" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div className="absolute inset-0 bg-background/80" />
          <aside id="mobile-nav" className="absolute inset-y-0 left-0 w-[280px] max-w-[85vw] border-r border-border bg-sidebar">{panel}</aside>
        </div>
      )}
    </>
  );
}
