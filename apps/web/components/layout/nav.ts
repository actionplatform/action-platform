import { Building2, Cloud, GitBranch, KeyRound, Users, UsersRound } from "lucide-react";

import type { LucideIcon } from "lucide-react";

export type SubPage = { href: string; label: string; icon: LucideIcon; exact?: boolean };

export const ORGANIZATION_PAGES: SubPage[] = [
  { href: "/organization/teams", label: "Teams", icon: UsersRound },
  { href: "/organization/members", label: "Members", icon: Users },
  { href: "/organization/sessions", label: "Sessions", icon: KeyRound },
];

export const INTEGRATIONS_PAGES: SubPage[] = [
  { href: "/integrations/hosts", label: "Code hosts", icon: GitBranch },
  { href: "/integrations/cloud", label: "Cloud", icon: Cloud },
];

export const SETTINGS_PAGES: SubPage[] = [{ href: "/settings", label: "General", icon: Building2, exact: true }];

export function pageActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
