import { Building2, Code2, Plug, Users } from "lucide-react";

import type { LucideIcon } from "lucide-react";

export type SettingsPage = { href: string; label: string; icon: LucideIcon; exact?: boolean };

export const SETTINGS_PAGES: SettingsPage[] = [
  { href: "/settings", label: "General", icon: Building2, exact: true },
  { href: "/settings/people", label: "People", icon: Users },
  { href: "/settings/integrations", label: "Integrations", icon: Plug },
  { href: "/settings/developers", label: "Developers", icon: Code2 },
];

export function settingsPageActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}
