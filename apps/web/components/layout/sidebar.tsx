"use client";

import { Activity, ArrowLeft, ChevronRight, Cloud, FolderGit2, LayoutDashboard, LayoutTemplate, Menu, Plug, Rocket, Settings, Shield, Target, Users, Workflow, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/logo";
import { appPath } from "@/lib/app-routes";
import type { Org } from "@/lib/types";
import { cn } from "@/lib/utils";
import { OrgSwitcher } from "./org-switcher";
import { CONNECT_PAGES, ORGANIZATION_PAGES, pageActive, type SubPage } from "./nav";
import { useScope } from "./scope";
import { UserMenu } from "./user-menu";

type Item = { href: string; label: string; icon: typeof FolderGit2; children?: SubPage[] };

const groups: { label: string; items: Item[] }[] = [
  {
    label: "Build",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/projects", label: "Projects", icon: FolderGit2 },
      { href: "/templates", label: "Templates", icon: LayoutTemplate },
    ],
  },
  {
    label: "Organization",
    items: [
      { href: "/connect", label: "Connect", icon: Plug, children: CONNECT_PAGES },
      { href: "/organization", label: "Team", icon: Users, children: ORGANIZATION_PAGES },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

const admin: Item = { href: "/admin", label: "Admin", icon: Shield };

export const appItems: { tab: string; label: string; icon: typeof FolderGit2 }[] = [
  { tab: "", label: "Overview", icon: LayoutDashboard },
  { tab: "releases", label: "Releases", icon: Rocket },
  { tab: "scopes", label: "Scopes", icon: Target },
  { tab: "deployments", label: "Deployments", icon: Cloud },
  { tab: "pipelines", label: "Pipelines", icon: Workflow },
  { tab: "activity", label: "Activity", icon: Activity },
  { tab: "settings", label: "Settings", icon: Settings },
];

const link = "mx-3 my-0.5 flex h-10 min-h-10 items-center gap-3 rounded-[7px] border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground";
const on = "border-border bg-surface-selected text-foreground";
const off = "border-transparent text-secondary hover:bg-surface-hover hover:text-foreground";

type Props = { versions: { web: string; api: string; lib: string }; user: { name: string; email: string }; org: Org; orgs: Org[]; showAdmin?: boolean };

export function Sidebar({ versions, user, org, orgs, showAdmin = false }: Props) {
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
        <button type="button" aria-label="Close navigation" onClick={() => setOpen(false)} className="ml-auto flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground md:hidden"><X className="size-4" /></button>
      </div>
      <div className="border-b border-border px-3 py-3">
        <OrgSwitcher org={org} orgs={orgs} />
      </div>
      {scope ? (
        <nav aria-label={scope.appName} className="flex-1 py-2">
          <Link href={`/projects/${scope.projectId}`} className={cn(link, off)}>
            <ArrowLeft className="size-[18px]" strokeWidth={1.75} />
            <span className="truncate">{scope.projectName}</span>
          </Link>
          <div className="mx-5 mb-1 mt-3 truncate font-mono text-xs text-muted-foreground">{scope.appName}</div>
          {appItems.map(({ tab, label, icon: Icon }) => {
            const href = appPath(scope.projectId, scope.appId, tab);
            const active = tab ? pageActive(pathname, href) : pathname === href;
            return (
              <Link
                key={label}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(link, active ? on : off)}
              >
                <Icon className="size-[18px]" strokeWidth={1.75} />
                {label}
              </Link>
            );
          })}
        </nav>
      ) : (
        <nav aria-label="Main" className="flex-1 overflow-y-auto py-2">
          {groups.map((group) => (
            <div key={group.label} className="mb-2">
              <div className="px-6 pb-1 pt-3 font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">{group.label}</div>
              {group.items.map((item) => (
                <NavItem key={item.href} item={item} pathname={pathname} isActive={isActive} />
              ))}
            </div>
          ))}
          {showAdmin && (
            <div className="mt-2 border-t border-border-subtle pt-2">
              <NavItem item={admin} pathname={pathname} isActive={isActive} />
            </div>
          )}
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
      <aside className="hidden md:block fixed inset-y-0 left-0 w-[280px] border-r border-border bg-sidebar xl:w-[304px]">{panel}</aside>

      <header className="md:hidden sticky top-0 z-30 flex h-14 items-center gap-2.5 border-b border-border bg-sidebar pl-4 pr-1.5">
        <Logo className="size-5" />
        <span className="truncate text-[15px] font-semibold">action-platform</span>
        <button type="button" aria-label="Open navigation" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(true)} className="ml-auto flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
          <Menu className="size-5" />
        </button>
      </header>

      {open && (
        <div className="md:hidden fixed inset-0 z-40" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div className="absolute inset-0 bg-background/80" />
          <aside id="mobile-nav" role="dialog" aria-modal="true" aria-label="Navigation" className="absolute inset-y-0 right-0 w-[300px] max-w-[88vw] border-l border-border bg-sidebar">{panel}</aside>
        </div>
      )}
    </>
  );
}

function NavItem({ item, pathname, isActive }: { item: Item; pathname: string; isActive: (href: string) => boolean }) {
  const { href, label, icon: Icon, children } = item;

  if (!children) {
    return (
      <Link href={href} aria-current={isActive(href) ? "page" : undefined} className={cn(link, isActive(href) ? on : off)}>
        <Icon className="size-[18px]" strokeWidth={1.75} />
        {label}
      </Link>
    );
  }

  return <NavGroup item={item} pages={children} pathname={pathname} active={isActive(href)} />;
}

function NavGroup({ item: { href, label, icon: Icon }, pages, pathname, active }: { item: Item; pages: SubPage[]; pathname: string; active: boolean }) {
  const [expanded, setExpanded] = useState(active);
  const id = `nav-${href.slice(1)}`;

  useEffect(() => {
    if (active) setExpanded(true);
  }, [active, pathname]);

  return (
    <div>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={id}
        onClick={() => setExpanded((v) => !v)}
        className={cn(link, "w-[calc(100%-1.5rem)] border-transparent text-left", active ? "bg-surface-selected text-foreground" : "text-secondary hover:bg-surface-hover hover:text-foreground")}
      >
        <Icon className="size-[18px]" strokeWidth={1.75} />
        <span className="flex-1">{label}</span>
        <ChevronRight className={cn("size-3.5 shrink-0 text-muted-foreground transition-transform duration-150", expanded && "rotate-90")} strokeWidth={1.75} />
      </button>
      {expanded && (
        <div id={id} className="mb-1 ml-[37px] mr-3 mt-0.5 border-l border-border-subtle pl-2">
          {pages.map((page) => {
            const current = pageActive(pathname, page.href, page.exact);
            return (
              <Link
                key={page.href}
                href={page.href}
                aria-current={current ? "page" : undefined}
                className={cn("flex h-8 items-center rounded-[6px] px-2.5 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground", current ? "bg-surface-hover text-foreground" : "text-secondary hover:text-foreground")}
              >
                {page.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
