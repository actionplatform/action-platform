"use client";

import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { stackMeta, templateIcon, typeMeta } from "@/lib/catalog";
import { Section, SelectCard } from "../parts";
import type { AppWizard } from "../use-app-wizard";

export function TemplateStep({ w }: { w: AppWizard }) {
  return (
    <Section title="Choose a template" description="Select the foundation that best fits your project.">
      <div className="grid gap-3 sm:grid-cols-2">
        {w.templates.map((t) => {
          const icon = templateIcon(w.matrix, t);
          return (
            <SelectCard key={`${t.source}:${t.template}`} selected={w.template === t.template && w.source === t.source} onClick={() => w.pickTemplate(t)}>
              {icon ? <BrandIcon src={icon} title={t.template} className="mt-0.5" /> : null}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-medium">{t.template}</span>
                  {t.default && <Badge tone="inverse">Default</Badge>}
                  {t.source !== "official" && <Badge className="font-mono">{t.source}</Badge>}
                </div>
                <div className="text-sm text-secondary mt-1">{t.description}</div>
                <div className="flex gap-2 mt-3 text-xs text-muted-foreground">
                  <span>{typeMeta(w.matrix, t.type).label}</span>
                  {t.stack && <><span>·</span><span>{stackMeta(w.matrix, t.stack).label}</span></>}
                </div>
              </div>
            </SelectCard>
          );
        })}
      </div>
    </Section>
  );
}
