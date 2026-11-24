"use client";

import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { switchOrganization } from "@/app/(app)/actions";
import type { Org } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useScope } from "./scope";

const STAYS = ["/dashboard"];

export function OrgSwitcher({ org, orgs }: { org: Org; orgs: Org[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const { switchingTo, setSwitchingTo } = useScope();
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (switchingTo === org.id) setSwitchingTo(null);
  }, [org.id, switchingTo, setSwitchingTo]);

  const choose = (id: string) => {
    setOpen(false);
    if (id === org.id) return;
    const next = STAYS.includes(pathname) ? pathname : "/projects";
    setSwitchingTo(id);
    start(async () => {
      try {
        await switchOrganization(id);
      } catch (e) {
        setSwitchingTo(null);
        throw e;
      }
      router.push(next);
      router.refresh();
    });
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 rounded-[7px] px-2.5 py-2 text-left text-sm hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
        aria-expanded={open}
      >
        <span className="flex size-8 items-center justify-center rounded-md border border-border bg-background"><Building2 className="size-4" strokeWidth={1.75} /></span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{org.name}</span>
          <span className="block truncate font-mono text-xs text-secondary">{org.slug}</span>
        </span>
        <ChevronsUpDown className="size-4 text-muted-foreground" />
      </button>

      {open && (
        <div className="absolute left-0 right-0 z-20 mt-1 rounded-md border border-border bg-surface p-1 shadow-none">
          {orgs.map((o) => (
            <button
              key={o.id}
              type="button"
              disabled={pending}
              onClick={() => choose(o.id)}
              className={cn("flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface-hover", o.id === org.id && "text-foreground")}
            >
              <span className="flex-1 truncate text-left">{o.name}</span>
              {o.id === org.id && <Check className="size-4" />}
            </button>
          ))}
          <div className="my-1 h-px bg-border" />
          <button
            type="button"
            onClick={() => { setOpen(false); router.push("/orgs/new"); }}
            className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-secondary hover:bg-surface-hover hover:text-foreground"
          >
            <Plus className="size-4" /> New organization
          </button>
        </div>
      )}
    </div>
  );
}
