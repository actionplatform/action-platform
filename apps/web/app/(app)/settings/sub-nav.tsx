"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { SETTINGS_PAGES, settingsPageActive } from "./nav";

export function SettingsSubNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings" className="-mx-5 mb-5 overflow-x-auto border-b border-border px-5 md:hidden">
      <ul className="flex gap-1">
        {SETTINGS_PAGES.map(({ href, label, exact }) => {
          const active = settingsPageActive(pathname, href, exact);
          return (
            <li key={href} className="shrink-0">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn("-mb-px flex h-11 items-center border-b-2 px-3 text-sm", active ? "border-foreground text-foreground" : "border-transparent text-secondary hover:text-foreground")}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
