import { Activity, Building2, KeyRound, ShieldCheck, Users, UsersRound } from "lucide-react";

import type { LucideIcon } from "lucide-react";

export type SubPage = { href: string; label: string; icon: LucideIcon; exact?: boolean };

export const ORGANIZATION_PAGES: SubPage[] = [
  { href: "/organization/teams", label: "Teams", icon: UsersRound },
  { href: "/organization/members", label: "Members", icon: Users },
  { href: "/organization/sessions", label: "Sessions", icon: KeyRound },
];

export const SETTINGS_PAGES: SubPage[] = [
  { href: "/settings", label: "General", icon: Building2, exact: true },
  { href: "/settings/access", label: "Access", icon: ShieldCheck },
  { href: "/settings/instance", label: "Instance", icon: Activity },
];

export function subNavPages(pages: SubPage[]): { href: string; label: string; exact?: boolean }[] {
  return pages.map(({ href, label, exact }) => ({ href, label, exact }));
}

export function pageActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
