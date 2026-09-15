"use client";

import { BrandIcon } from "@/components/ui/brand-icon";
import { countFor, stackMeta } from "@/lib/catalog";
import { plural } from "../model";
import { Section, SelectCard } from "../parts";
import type { AppWizard } from "../use-app-wizard";

export function StackStep({ w }: { w: AppWizard }) {
  return (
    <Section title="Choose your stack" description="Select the language or runtime for your project.">
      <div className="grid gap-3 sm:grid-cols-3">
        {w.stacks.map((id) => {
          const m = stackMeta(w.matrix, id);
          return (
            <SelectCard key={id} selected={w.stack === id} onClick={() => w.pickStack(id)} compact>
              {m.icon ? <BrandIcon src={m.icon} title={m.label} /> : <span className="size-5 shrink-0 rounded-sm border border-border" />}
              <div className="min-w-0 flex-1">
                <div className="font-medium">{m.label}</div>
                <div className="text-xs text-muted-foreground">{plural(countFor(w.matrix, w.type!, id), "template")}</div>
              </div>
            </SelectCard>
          );
        })}
      </div>
    </Section>
  );
}
