"use client";

import { ArrowRight, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Matrix } from "@/lib/api";
import { stackMeta, typeMeta } from "@/lib/catalog";
import { CONTINUE, type HostOption, type Preset, type ProjectOption } from "./model";
import { Summary } from "./parts";
import { Stepper } from "./stepper";
import { ConfigurationStep } from "./steps/configuration-step";
import { ReviewStep } from "./steps/review-step";
import { StackStep } from "./steps/stack-step";
import { TemplateStep } from "./steps/template-step";
import { TypeStep } from "./steps/type-step";
import { useAppWizard } from "./use-app-wizard";

export function Wizard(props: { matrix: Matrix; preset: Preset; projectId: string | null; projects: ProjectOption[]; hosts: HostOption[] }) {
  const w = useAppWizard(props);
  const { step, matrix } = w;

  return (
    <div className="space-y-6">
      <Stepper current={step} onJump={w.setStep} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 space-y-6">
          {step === 0 && <TypeStep w={w} />}
          {step === 1 && <StackStep w={w} />}
          {step === 2 && <TemplateStep w={w} />}
          {step === 3 && <ConfigurationStep w={w} />}
          {step === 4 && <ReviewStep w={w} />}
        </div>

        <Summary
          type={w.type ? typeMeta(matrix, w.type).label : null}
          stack={w.stack ? stackMeta(matrix, w.stack).label : w.hasStack || !w.type ? null : "—"}
          template={w.template}
          configuration={w.config.name ? `${w.config.name} · ${w.config.directory}` : null}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button variant="ghost" onClick={w.cancel}>Cancel</Button>
        <div className="flex gap-2 ml-auto">
          {(step > 0 || w.preset) && <Button variant="outline" onClick={w.back} disabled={w.pending}>Back</Button>}
          <Button onClick={step === 4 ? w.submit : w.next} disabled={!w.canContinue || w.pending}>
            {w.pending ? "Creating…" : CONTINUE[step]}
            {step < 4 ? <ArrowRight className="size-4" /> : <Check className="size-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
