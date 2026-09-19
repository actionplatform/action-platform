import type { Schemas } from "./api";

export type Scope = Schemas["ScopeRow"];
export type Scopes = Schemas["Scopes"];
export type ScopeRequest = Schemas["ScopeRequest"];
export type Criticality = "test" | "low" | "medium" | "high" | "critical";
export type Shape = "candidate" | "stable" | "hotfix";

export const CRITICALITY: Record<Criticality, { label: string; tone: "neutral" | "warning" | "danger" | "success"; hint: string }> = {
  test: { label: "Test", tone: "neutral", hint: "No production use." },
  low: { label: "Low", tone: "neutral", hint: "Little impact; downtime is tolerable." },
  medium: { label: "Medium", tone: "warning", hint: "Affects processes, but a manual alternative exists." },
  high: { label: "High", tone: "danger", hint: "Affects important operations and many users." },
  critical: { label: "Critical", tone: "danger", hint: "Essential to the business: stops operations, causes financial loss or legal risk." },
};

export const ACCEPTS: Record<Criticality, Shape[]> = {
  test: ["candidate", "stable", "hotfix"],
  low: ["candidate", "stable", "hotfix"],
  medium: ["stable", "hotfix"],
  high: ["stable", "hotfix"],
  critical: ["stable", "hotfix"],
};

export function shapeOf(version: string): Shape {
  return version.replace(/^v/, "").split("+")[0].includes("-") ? "candidate" : "stable";
}
