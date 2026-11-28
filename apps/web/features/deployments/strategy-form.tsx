"use client";

import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { Field, Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  type CanaryStep,
  type Config,
  type JsonSchema,
  type Safety,
  type StrategyDef,
  type StrategySupport,
  STRATEGY_COPY,
  canaryError,
  supportOf,
  weightPath,
} from "./strategies";

const titleOf = (key: string) => key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export function StrategyPicker({ strategies, support, value, onChange }: { strategies: StrategyDef[]; support: StrategySupport[] | null; value: string; onChange: (id: string) => void }) {
  return (
    <div role="radiogroup" aria-label="Deployment strategy" className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {strategies.map((s) => {
        const sup = supportOf(support, s.id);
        const selected = value === s.id;
        const text = STRATEGY_COPY[s.id]?.text ?? s.description;
        return (
          <label
            key={s.id}
            className={cn(
              "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors focus-within:ring-1 focus-within:ring-foreground",
              selected ? "border-foreground bg-surface-hover" : "border-border hover:border-border-hover hover:bg-surface-hover",
              !sup.supported && "cursor-not-allowed opacity-50 hover:border-border hover:bg-transparent",
            )}
          >
            <input type="radio" name="deployment-strategy" className="sr-only" value={s.id} checked={selected} disabled={!sup.supported} onChange={() => onChange(s.id)} />
            <CheckIndicator selected={selected} className="mt-0.5" />
            <span className="min-w-0">
              <span className="block text-sm font-medium">{STRATEGY_COPY[s.id]?.label ?? s.label}</span>
              <span className="block text-[13px] text-secondary">{text}</span>
              {!sup.supported && <span className="mt-1 block text-xs text-muted-foreground">{sup.reason ?? "Not supported for this scope."}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
}

function CanarySteps({ steps, onChange }: { steps: CanaryStep[]; onChange: (steps: CanaryStep[]) => void }) {
  const set = (i: number, patch: Partial<CanaryStep>) => onChange(steps.map((s, at) => (at === i ? { ...s, ...patch } : s)));
  const error = canaryError(steps);
  const last = steps[steps.length - 1];
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-secondary">
        <span>Steps</span>
        <span className="font-mono" aria-label="Weight progression">{weightPath(steps)}</span>
      </div>
      <ul className="space-y-2">
        {steps.map((s, i) => (
          <li key={i} className="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
            <Field label={i === 0 ? "Weight (%)" : ""}>
              <Input type="number" min={1} max={100} aria-label={`Step ${i + 1} weight`} value={Number.isFinite(s.weight) ? s.weight : ""} onChange={(e) => set(i, { weight: e.target.valueAsNumber })} />
            </Field>
            <Field label={i === 0 ? "Pause (seconds)" : ""}>
              <Input type="number" min={0} aria-label={`Step ${i + 1} pause`} value={Number.isFinite(s.pause_seconds) ? s.pause_seconds : ""} onChange={(e) => set(i, { pause_seconds: e.target.valueAsNumber })} />
            </Field>
            <Button type="button" size="icon" variant="ghost" aria-label={`Remove step ${i + 1}`} disabled={steps.length <= 1} onClick={() => onChange(steps.filter((_, at) => at !== i))}>
              <X className="size-4" strokeWidth={1.75} />
            </Button>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-3">
        <Button type="button" size="sm" variant="outline" onClick={() => onChange([...steps, { weight: Math.min(100, (last?.weight ?? 0) + 25), pause_seconds: 300 }])}>
          <Plus className="size-3.5" strokeWidth={1.75} /> Add step
        </Button>
        {error && <span role="alert" className="text-xs text-status-bad">{error}</span>}
      </div>
    </div>
  );
}

function Scalar({ name, spec, value, onChange }: { name: string; spec: JsonSchema; value: unknown; onChange: (value: unknown) => void }) {
  const label = spec.title ?? titleOf(name);
  if (spec.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="size-4 accent-foreground" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
        {label}
      </label>
    );
  }
  const hint = [spec.minimum !== undefined ? `min ${spec.minimum}` : null, spec.maximum !== undefined ? `max ${spec.maximum}` : null].filter(Boolean).join(" · ");
  return (
    <Field label={label} hint={spec.description ?? (hint || undefined)}>
      <Input type="number" min={spec.minimum} max={spec.maximum} value={typeof value === "number" && Number.isFinite(value) ? value : ""} onChange={(e) => onChange(e.target.valueAsNumber)} />
    </Field>
  );
}

export function SchemaForm({ schema, value, onChange }: { schema: JsonSchema; value: Config; onChange: (value: Config) => void }) {
  const entries = Object.entries(schema.properties ?? {});
  if (entries.length === 0) return null;
  return (
    <div className="space-y-3">
      {entries.map(([name, spec]) =>
        spec.type === "array" && name === "steps" ? (
          <CanarySteps key={name} steps={(value[name] as CanaryStep[]) ?? []} onChange={(steps) => onChange({ ...value, [name]: steps })} />
        ) : (
          <Scalar key={name} name={name} spec={spec} value={value[name]} onChange={(v) => onChange({ ...value, [name]: v })} />
        ),
      )}
    </div>
  );
}

export function SafetyFields({ schema, value, onChange }: { schema: JsonSchema; value: Safety; onChange: (value: Safety) => void }) {
  const props = schema.properties ?? {};
  const bake = props.bake_seconds;
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="size-4 accent-foreground" checked={value.auto_rollback} onChange={(e) => onChange({ ...value, auto_rollback: e.target.checked })} />
        Automatic rollback
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="size-4 accent-foreground" checked={value.manual_approval} onChange={(e) => onChange({ ...value, manual_approval: e.target.checked })} />
        Require manual approval
      </label>
      <Field label="Bake time (seconds)" hint="How long the new version is observed before the old one is retired." className="max-w-xs">
        <Input type="number" min={bake?.minimum ?? 0} value={Number.isFinite(value.bake_seconds) ? value.bake_seconds : ""} onChange={(e) => onChange({ ...value, bake_seconds: e.target.valueAsNumber })} />
      </Field>
    </div>
  );
}
