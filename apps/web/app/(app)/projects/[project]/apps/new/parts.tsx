"use client";

import { Check, Copy } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { cn } from "@/lib/utils";

export function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-secondary">{description}</p>
      </div>
      {children}
    </section>
  );
}

export function SelectCard({ selected, onClick, children, compact }: { selected: boolean; onClick: () => void; children: React.ReactNode; compact?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "flex items-start gap-3 rounded-lg border bg-surface text-left transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground",
        compact ? "p-3" : "p-4",
        selected ? "border-foreground" : "border-border hover:border-border-hover hover:bg-surface-hover",
      )}
    >
      {children}
      <CheckIndicator selected={selected} className="mt-0.5" />
    </button>
  );
}

export function Option({ checked, disabled, onChange, label, hint, children }: { checked: boolean; disabled?: boolean; onChange: (v: boolean) => void; label: string; hint?: string; children?: React.ReactNode }) {
  return (
    <div className={cn("rounded-md border border-border p-3", disabled && "opacity-50")}>
      <label className="flex items-start gap-3 cursor-pointer">
        <button
          type="button"
          role="checkbox"
          aria-checked={checked}
          disabled={disabled}
          onClick={() => onChange(!checked)}
          className={cn("mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-sm border", checked ? "border-foreground bg-foreground text-primary-foreground" : "border-border-hover")}
        >
          {checked && <Check className="size-3" strokeWidth={3} />}
        </button>
        <span className="min-w-0 flex-1">
          <span className="block text-sm">{label}</span>
          {hint && <span className="block text-xs text-muted-foreground mt-0.5">{hint}</span>}
          {children}
        </span>
      </label>
    </div>
  );
}

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("rounded-md border px-2.5 py-1 text-xs font-mono transition-colors", active ? "border-foreground bg-foreground text-primary-foreground" : "border-border text-foreground hover:border-border-hover")}
    >
      {children}
    </button>
  );
}

export function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-secondary mb-0.5">{k}</div>
      <div className={cn("break-words", mono && "font-mono text-xs")}>{v}</div>
    </div>
  );
}

export function CommandPreview({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <div className="text-xs text-secondary mb-1">Equivalent command</div>
      <div className="relative rounded-md border border-border bg-background p-3 pr-10 font-mono text-xs overflow-x-auto">
        <code>{command}</code>
        <button
          type="button"
          title="Copy"
          onClick={() => { navigator.clipboard?.writeText(command); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
          className="absolute right-2 top-2 text-secondary hover:text-foreground"
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </button>
      </div>
    </div>
  );
}

export function Summary({ type, stack, template, configuration }: { type: string | null; stack: string | null; template: string | null; configuration: string | null }) {
  return (
    <Card className="h-fit lg:sticky lg:top-8">
      <CardHeader><CardTitle>Your selection</CardTitle></CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Row k="Type" v={type ?? "—"} />
        <Row k="Stack" v={stack ?? "—"} />
        <Row k="Template" v={template ?? "—"} mono />
        <Row k="Configuration" v={configuration ?? "—"} />
        <Link href="/templates" className="block text-xs text-secondary underline underline-offset-4 hover:text-foreground">Browse the catalog</Link>
      </CardContent>
    </Card>
  );
}
