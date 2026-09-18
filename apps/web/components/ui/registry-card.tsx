"use client";

import type { LucideIcon } from "lucide-react";
import { Plus, X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./button";
import { EmptyState } from "./empty-state";
import { Panel, PanelHeader } from "./panel";

type Props = {
  title: string;
  description?: ReactNode;
  addLabel?: string;
  canAdd: boolean;
  open: boolean;
  onToggle: () => void;
  form: ReactNode;
  empty: { icon: LucideIcon; title: string; text?: ReactNode };
  count: number;
  aside?: ReactNode;
  children: ReactNode;
};

export function RegistryCard({ title, description, addLabel = "Add", canAdd, open, onToggle, form, empty, count, aside, children }: Props) {
  return (
    <Panel>
      <PanelHeader
        title={title}
        description={description}
        aside={
          <div className="flex items-center gap-2">
            {aside}
            {canAdd && <Button size="sm" variant="outline" onClick={onToggle}>{open ? <X className="size-3.5" strokeWidth={2} /> : <Plus className="size-3.5" strokeWidth={2} />} {open ? "Close" : addLabel}</Button>}
          </div>
        }
      />
      {open && <div className="border-b border-border bg-background/40 px-4 py-4">{form}</div>}
      {count === 0 ? <EmptyState icon={empty.icon} title={empty.title} text={empty.text} /> : <ul className="divide-y divide-border-subtle">{children}</ul>}
    </Panel>
  );
}
