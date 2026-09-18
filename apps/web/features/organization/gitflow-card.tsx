"use client";

import { ChevronDown, Info } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { cn } from "@/lib/utils";

type Rules = { kinds: string[]; protected: string[]; types: string[] };

export function GitflowCard({ rules }: { rules: Rules | null }) {
  const [open, setOpen] = useState(false);

  return (
    <Panel>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-hover/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold">Git-flow rules <Info className="size-3.5 text-muted-foreground" strokeWidth={1.75} aria-label="Enforced by the git hooks, the CI and the platform" /></h2>
          <p className="mt-1 text-[13px] text-secondary">Configure how branches, pull requests and releases work in this workspace.</p>
        </div>
        <ChevronDown className={cn("mt-1 size-4 shrink-0 text-muted-foreground transition-transform duration-150", open && "rotate-180")} strokeWidth={1.75} />
      </button>
      {open && (
        <div className="border-t border-border p-4 text-sm">
          {!rules ? (
            <p className="text-secondary">Rules come from the API; it is offline.</p>
          ) : (
            <div className="grid gap-5 sm:grid-cols-3">
              <Section title="Branch kinds" hint="Work happens on <kind>/<code> branches."><Chips items={rules.kinds.map((k) => `${k}/`)} /></Section>
              <Section title="Protected branches" hint="No direct commits; only chore(release) and chore(platform)."><Chips items={rules.protected} /></Section>
              <Section title="Commit types" hint="Conventional Commits 1.0.0."><Chips items={rules.types.map((t) => `${t}:`)} /></Section>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function Section({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{title}</div>
      <div className="mt-2">{children}</div>
      <p className="mt-2 text-[12px] text-muted-foreground">{hint}</p>
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  return <div className="flex flex-wrap gap-1.5">{items.map((i) => <Badge key={i} className="h-6 bg-background px-2 font-mono text-[12px]">{i}</Badge>)}</div>;
}
