"use client";

import { countFor } from "@/lib/catalog";
import { plural } from "../model";
import { Section, SelectCard } from "../parts";
import type { AppWizard } from "../use-app-wizard";

export function TypeStep({ w }: { w: AppWizard }) {
  return (
    <Section title="What are you building?" description="Select a project type to get started.">
      <div className="grid gap-3 sm:grid-cols-2">
        {w.types.map((t) => (
          <SelectCard key={t.id} selected={w.type === t.id} onClick={() => w.pickType(t.id)}>
            <t.icon className="size-5 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="font-medium">{t.label}</div>
              <div className="text-sm text-secondary mt-0.5">{t.description}</div>
              <div className="text-xs text-muted-foreground mt-2">{plural(countFor(w.matrix, t.id), "template")}</div>
            </div>
          </SelectCard>
        ))}
      </div>
    </Section>
  );
}
