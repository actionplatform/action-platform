"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./button";
import { Panel, PanelBody, PanelHeader } from "./panel";
import { cn } from "@/lib/utils";

export type ActionButton = { label: string; onClick: () => void; icon?: LucideIcon; disabled?: boolean; busy?: boolean; busyLabel?: string };

type Props = {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  alerts?: ReactNode;
  primary: ActionButton;
  secondary?: ActionButton;
  blocker?: string | null;
  dialogs?: ReactNode;
  summary?: { label: string; value: string }[];
};

function Spinner({ light }: { light?: boolean }) {
  return <span className={cn("size-3.5 animate-spin rounded-full border-2", light ? "border-primary-foreground/40 border-t-primary-foreground" : "border-border border-t-foreground")} />;
}

function Action({ button, variant }: { button: ActionButton; variant: "default" | "outline" }) {
  const Icon = button.icon;
  return (
    <Button className="w-full sm:w-auto" variant={variant} disabled={button.disabled || button.busy} onClick={button.onClick}>
      {button.busy ? <Spinner light={variant === "default"} /> : Icon ? <Icon className="size-4" strokeWidth={1.75} /> : null} {button.busy ? (button.busyLabel ?? button.label) : button.label}
    </Button>
  );
}

export function ActionForm({ title, aside, children, alerts, primary, secondary, blocker, dialogs, summary }: Props) {
  return (
    <Panel>
      <PanelHeader title={title} aside={aside} />
      <PanelBody className="space-y-5">
        {children}
        {summary && <ActionSummary columns={4} items={summary} className="rounded-md border border-border-subtle bg-background px-4 py-3" />}
        {alerts}
        <div className="flex flex-col gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:items-center">
          <Action button={primary} variant="default" />
          {secondary && <Action button={secondary} variant="outline" />}
          {blocker && <div className="text-[13px] text-muted-foreground sm:ml-auto">{blocker}</div>}
        </div>
      </PanelBody>
      {dialogs}
    </Panel>
  );
}

export function ActionFields({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-2", className)}>{children}</div>;
}

export function ActionField({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-secondary">{label} {hint}</div>
      {children}
    </div>
  );
}

export function ActionSummary({ items, columns = 2, className }: { items: { label: string; value: string }[]; columns?: 2 | 4; className?: string }) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-2 text-sm", columns === 4 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2", className)}>
      {items.map((i) => (
        <div key={i.label} className="min-w-0">
          <dt className="text-xs text-secondary">{i.label}</dt>
          <dd className="truncate font-mono text-[13px] text-foreground" title={i.value}>{i.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ActionSteps({ steps }: { steps: ReactNode[] }) {
  return (
    <div className="mt-4 border-t border-border-subtle pt-3">
      <div className="text-xs text-secondary">This will</div>
      <ul className="mt-2 space-y-1.5 text-sm text-secondary">
        {steps.map((s, i) => (
          <li key={i} className="flex items-start gap-2"><span aria-hidden className="mt-[7px] size-1.5 shrink-0 rounded-full bg-foreground/60" /><span className="min-w-0">{s}</span></li>
        ))}
      </ul>
    </div>
  );
}

export function Running({ label, detail }: { label: string; detail?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border border-l-2 border-l-status-warn bg-surface px-3 py-2.5 text-sm">
      <span className="size-2 animate-pulse rounded-full bg-status-warn" />
      <span className="font-medium">{label}</span>
      {detail && <span className="text-secondary">{detail}</span>}
    </div>
  );
}
