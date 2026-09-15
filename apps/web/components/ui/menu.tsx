"use client";

import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export type MenuItem = { label: string; onSelect: () => void; danger?: boolean; icon?: ReactNode };

export function Menu({ trigger, items, align = "end", label }: { trigger: (props: { open: boolean; toggle: () => void; id: string | undefined }) => ReactNode; items: (MenuItem | "separator")[]; align?: "start" | "end"; label: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      {trigger({ open, toggle: () => setOpen((v) => !v), id: open ? id : undefined })}
      {open && (
        <div id={id} role="menu" aria-label={label} className={cn("absolute z-20 mt-1 min-w-44 rounded-lg border border-border bg-surface p-1", align === "end" ? "right-0" : "left-0")}>
          {items.map((item, i) =>
            item === "separator" ? (
              <div key={i} role="separator" className="my-1 h-px bg-border-subtle" />
            ) : (
              <button
                key={i}
                type="button"
                role="menuitem"
                onClick={() => { setOpen(false); item.onSelect(); }}
                className={cn("flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm hover:bg-surface-hover focus-visible:outline-none focus-visible:bg-surface-hover", item.danger ? "text-foreground" : "text-secondary hover:text-foreground")}
              >
                {item.icon}
                {item.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
