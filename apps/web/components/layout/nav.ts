import { Bell, Cloud, GitBranch, KeyRound, Radar, ShieldCheck, Users, UsersRound, Workflow } from "lucide-react";

import type { LucideIcon } from "lucide-react";

export type SubPage = { href: string; label: string; icon: LucideIcon; exact?: boolean };

export const CONNECT_PAGES: SubPage[] = [
  { href: "/connect/git", label: "Git", icon: GitBranch },
  { href: "/connect/ci", label: "CI", icon: Workflow },
  { href: "/connect/deploy", label: "Deploy", icon: Cloud },
  { href: "/connect/observability", label: "Observability", icon: Radar },
  { href: "/connect/notifications", label: "Notifications", icon: Bell },
];

export const ORGANIZATION_PAGES: SubPage[] = [
  { href: "/organization/members", label: "Members", icon: Users },
  { href: "/organization/teams", label: "Teams", icon: UsersRound },
  { href: "/organization/access", label: "Access", icon: ShieldCheck },
  { href: "/organization/sessions", label: "Sessions", icon: KeyRound },
];

export function subNavPages(pages: SubPage[]): { href: string; label: string; exact?: boolean }[] {
  return pages.map(({ href, label, exact }) => ({ href, label, exact }));
}

export function pageActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
