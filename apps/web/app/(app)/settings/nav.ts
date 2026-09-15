import { Building2, GitBranch, KeyRound, Plug, Users } from "lucide-react";

import type { LucideIcon } from "lucide-react";

export type SettingsPage = { href: string; label: string; icon: LucideIcon; exact?: boolean };

export const SETTINGS_PAGES: SettingsPage[] = [
  { href: "/settings", label: "General", icon: Building2, exact: true },
  { href: "/settings/members", label: "Members", icon: Users },
  { href: "/settings/hosts", label: "Code hosts", icon: Plug },
  { href: "/settings/gitflow", label: "Git-flow", icon: GitBranch },
  { href: "/settings/api", label: "API", icon: KeyRound },
];

export function settingsPageActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
