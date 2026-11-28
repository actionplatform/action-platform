import type { Protection, ProtectionState, RuleMode } from "@/lib/protection";

export type Setting = "default" | "on" | "off";

export const MODE_LABEL: Record<RuleMode, string> = { native: "Enforced by the host", check: "Required check", inactive: "Not active" };
export const MODE_TONE: Record<RuleMode, "success" | "info" | "warning"> = { native: "success", check: "info", inactive: "warning" };

export function settingOf(p: Pick<Protection, "enforce" | "source">): Setting {
  if (p.source === "organization") return "default";
  return p.enforce ? "on" : "off";
}

export function enforceOf(setting: Setting): boolean | null {
  return setting === "default" ? null : setting === "on";
}

export function counts(state: ProtectionState | null | undefined): Record<RuleMode, number> {
  const out: Record<RuleMode, number> = { native: 0, check: 0, inactive: 0 };
  for (const r of state?.rules ?? []) if (r.mode in out) out[r.mode as RuleMode] += 1;
  return out;
}

export type Summary = { tone: "success" | "warning" | "neutral" | "danger"; label: string; detail: string };

export function summaryOf(p: Protection | null): Summary {
  if (!p) return { tone: "neutral", label: "Unknown", detail: "The platform could not read the protection of this app." };
  const state: ProtectionState | null | undefined = p.state;
  if (!p.enforce) {
    if (state?.active) return { tone: "neutral", label: "Not enforced", detail: "The host still has rules applied earlier; the platform no longer keeps them." };
    return { tone: "neutral", label: "Not enforced", detail: "The code host does not enforce git-flow for this app; hooks and CI checks only." };
  }
  if (!state) return { tone: "warning", label: "Pending", detail: "Enforced but not applied yet: the next hourly check applies it, or Apply now in the app Settings." };
  if (state.error && !state.active) return { tone: "danger", label: "Not active", detail: state.error };
  if (state.error) return { tone: "warning", label: "Not kept", detail: `Rules are on the host, but the platform cannot keep them: ${state.error}` };
  const n = counts(state);
  if (state.drift.length > 0) return { tone: "warning", label: "Drifted", detail: `${state.drift.length} difference(s) from the policy; the next check puts them back.` };
  return { tone: n.inactive > 0 ? "warning" : "success", label: n.inactive > 0 ? "Partly active" : "Active", detail: `${n.native} enforced by ${state.host}, ${n.check} by required checks, ${n.inactive} not active.` };
}
