"use client";

import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { switchOrganization } from "@/app/(app)/actions";
import type { Org } from "@/lib/types";
import { cn } from "@/lib/utils";

export function OrgSwitcher({ org, orgs }: { org: Org; orgs: Org[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-hover"
        aria-expanded={open}
      >
        <span className="flex size-6 items-center justify-center rounded border border-border bg-background"><Building2 className="size-3.5" /></span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{org.name}</span>
          <span className="block truncate text-xs text-muted-foreground">{org.slug}</span>
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
              onClick={() => { setOpen(false); if (o.id !== org.id) start(async () => { await switchOrganization(o.id); router.push("/projects"); router.refresh(); }); }}
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
