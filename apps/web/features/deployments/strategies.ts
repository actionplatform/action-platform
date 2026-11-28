export type JsonSchema = {
  type?: string;
  title?: string;
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  required?: string[];
};

export type StrategyDef = { id: string; label: string; description: string; config_schema: JsonSchema; needs?: string[] };
export type StrategySupport = { id: string; supported: boolean; reason?: string | null };
export type Safety = { auto_rollback: boolean; manual_approval: boolean; bake_seconds: number };
export type Config = Record<string, unknown>;
export type CanaryStep = { weight: number; pause_seconds: number };

export type DeploymentStep = {
  index: number;
  kind: string;
  status: string;
  params?: Record<string, unknown> | null;
  detail?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  data?: Record<string, unknown> | null;
};

export const DEFAULT_STRATEGY = "recreate";

export const STRATEGY_COPY: Record<string, { label: string; text: string }> = {
  recreate: { label: "Recreate", text: "Replace all instances at once." },
  rolling: { label: "Rolling", text: "Gradually replace existing instances." },
  blue_green: { label: "Blue-Green", text: "Switch traffic between environments." },
  canary: { label: "Canary", text: "Progressively shift production traffic." },
  shadow: { label: "Shadow", text: "Mirror traffic to a new version." },
};

export const STRATEGY_ORDER = ["recreate", "rolling", "blue_green", "canary", "shadow"];

export const labelOf = (id: string | null | undefined, fallback?: string): string => (id ? (STRATEGY_COPY[id]?.label ?? fallback ?? id) : "Recreate");

export const FALLBACK_STRATEGIES: StrategyDef[] = STRATEGY_ORDER.map((id) => ({ id, label: STRATEGY_COPY[id].label, description: STRATEGY_COPY[id].text, config_schema: { type: "object", properties: {} } }));

export const FALLBACK_SAFETY: JsonSchema = {
  type: "object",
  properties: {
    auto_rollback: { type: "boolean", default: true },
    manual_approval: { type: "boolean", default: false },
    bake_seconds: { type: "integer", minimum: 0, default: 0 },
  },
};

export function defaultOf(schema: JsonSchema): unknown {
  if (schema.default !== undefined) return structuredClone(schema.default);
  if (schema.type === "object") return Object.fromEntries(Object.entries(schema.properties ?? {}).map(([k, s]) => [k, defaultOf(s)]));
  if (schema.type === "array") return [];
  if (schema.type === "boolean") return false;
  if (schema.type === "integer" || schema.type === "number") return schema.minimum ?? 0;
  return "";
}

export function defaultsOf(schema: JsonSchema | undefined): Config {
  return schema ? (defaultOf({ ...schema, default: undefined }) as Config) : {};
}

export function safetyDefaults(schema: JsonSchema | undefined): Safety {
  const found = defaultsOf(schema ?? FALLBACK_SAFETY);
  return { auto_rollback: found.auto_rollback !== false, manual_approval: found.manual_approval === true, bake_seconds: typeof found.bake_seconds === "number" ? found.bake_seconds : 0 };
}

export function supportOf(list: StrategySupport[] | null, id: string): StrategySupport {
  return list?.find((s) => s.id === id) ?? { id, supported: id === DEFAULT_STRATEGY || list === null };
}

export function weightPath(steps: CanaryStep[]): string {
  const weights = steps.map((s) => s.weight).filter((w) => Number.isFinite(w));
  return weights.length > 0 ? weights.map((w) => `${w}%`).join(" → ") : "—";
}

export function canaryError(steps: CanaryStep[]): string | null {
  if (steps.length === 0) return "Add at least one step.";
  if (steps.some((s) => !Number.isInteger(s.weight) || s.weight < 1 || s.weight > 100)) return "Each weight is between 1 and 100.";
  if (steps.some((s) => !Number.isInteger(s.pause_seconds) || s.pause_seconds < 0)) return "A pause cannot be negative.";
  if (steps[steps.length - 1].weight !== 100) return "The last step must reach 100%.";
  return null;
}

export function duration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return seconds % 60 === 0 ? `${seconds / 60}m` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return seconds % 3600 === 0 ? `${seconds / 3600}h` : `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}

export function configSummary(id: string | null | undefined, config: Config | null | undefined): string[] {
  const c = config ?? {};
  const num = (k: string) => (typeof c[k] === "number" ? (c[k] as number) : null);
  const out: string[] = [];
  if (id === "rolling") {
    if (num("batch_percent") !== null) out.push(`${num("batch_percent")}% per batch`);
    if (num("pause_seconds") !== null) out.push(`${duration(num("pause_seconds")!)} between batches`);
  } else if (id === "blue_green") {
    if (num("bake_seconds") !== null) out.push(`${duration(num("bake_seconds")!)} bake`);
    if (num("keep_old_seconds") !== null) out.push(`keep old ${duration(num("keep_old_seconds")!)}`);
  } else if (id === "canary") {
    const steps = Array.isArray(c.steps) ? (c.steps as CanaryStep[]) : [];
    if (steps.length > 0) out.push(weightPath(steps));
  } else if (id === "shadow") {
    if (num("duration_seconds") !== null) out.push(`mirror for ${duration(num("duration_seconds")!)}`);
  }
  return out;
}

export const STEP_LABELS: Record<string, string> = {
  deploy_new: "Deploy new version",
  shift: "Shift traffic",
  mirror: "Mirror traffic",
  replace: "Replace instances",
  retire_old: "Retire old version",
  rollback: "Roll back",
  health: "Health check",
  pause: "Wait",
  approval: "Manual approval",
  native: "Run natively",
};

export const stepLabel = (kind: string): string => STEP_LABELS[kind] ?? kind.replace(/_/g, " ");

export function stepWeight(step: DeploymentStep): number | null {
  const p = step.params ?? {};
  if (step.kind === "shift" && typeof p.weight === "number") return p.weight;
  if (step.kind === "replace" && typeof p.upto === "number") return p.upto;
  return null;
}

export type StepTone = "done" | "active" | "failed" | "waiting" | "skipped";

export function stepTone(status: string): StepTone {
  if (["succeeded", "done", "ok", "completed"].includes(status)) return "done";
  if (["running", "in_progress", "rolling_back"].includes(status)) return "active";
  if (["failed", "error", "rolled_back"].includes(status)) return "failed";
  if (["paused", "awaiting_approval"].includes(status)) return "waiting";
  if (["skipped", "aborted", "cancelled"].includes(status)) return "skipped";
  return "skipped";
}

export function stepDetail(step: DeploymentStep): string | null {
  const p = step.params ?? {};
  if (step.kind === "pause" && typeof p.seconds === "number") return `${duration(p.seconds)}${typeof p.reason === "string" ? ` · ${p.reason.replace(/_/g, " ")}` : ""}`;
  if (step.kind === "replace" && typeof p.batch_percent === "number") return `${p.batch_percent}% per batch`;
  if (step.kind === "mirror") return p.on === false ? "off" : "on";
  return null;
}

export function currentWeight(steps: DeploymentStep[]): number | null {
  let found: number | null = null;
  for (const s of steps) {
    const w = stepWeight(s);
    if (w !== null && stepTone(s.status) === "done") found = w;
  }
  const active = steps.find((s) => stepTone(s.status) === "active" && stepWeight(s) !== null);
  if (active) return found ?? 0;
  if (found === null && steps.some((s) => s.kind === "deploy_new" && stepTone(s.status) === "done")) return 0;
  return found;
}

export const ACTIVE_STATES = ["queued", "running", "paused", "awaiting_approval", "rolling_back"];

export const STATE_TONES: Record<string, "danger" | "warning" | "success" | "neutral" | "info"> = {
  queued: "neutral",
  running: "warning",
  paused: "info",
  awaiting_approval: "info",
  rolling_back: "warning",
  rolled_back: "danger",
  aborted: "neutral",
  failed: "danger",
  done: "success",
  succeeded: "success",
};

export const STATE_LABELS: Record<string, string> = {
  paused: "Paused",
  awaiting_approval: "Awaiting approval",
  rolling_back: "Rolling back",
  rolled_back: "Rolled back",
  aborted: "Aborted",
};

export type Control = "promote" | "pause" | "resume" | "abort";

export function controlsFor(state: string, canDeploy: boolean): Control[] {
  if (!canDeploy) return [];
  switch (state) {
    case "running": return ["pause", "abort"];
    case "paused": return ["resume", "promote", "abort"];
    case "awaiting_approval": return ["promote", "abort"];
    case "rolling_back": return [];
    default: return [];
  }
}
