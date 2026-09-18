"use client";

import { cn } from "@/lib/utils";

export type Segment<T extends string> = { id: T; label: string };

export function SegmentedControl<T extends string>({ value, options, onChange, label, className }: { value: T; options: Segment<T>[]; onChange: (v: T) => void; label: string; className?: string }) {
  return (
    <div role="radiogroup" aria-label={label} className={cn("grid h-10 w-full overflow-hidden rounded-[7px] border border-border sm:inline-flex sm:w-auto", className)} style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((o) => (
        <button key={o.id} type="button" role="radio" aria-checked={value === o.id} onClick={() => onChange(o.id)} className={cn("px-4 text-sm transition-colors focus-visible:outline-none focus-visible:bg-surface-hover", value === o.id ? "bg-surface-selected text-foreground" : "text-secondary hover:text-foreground")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
