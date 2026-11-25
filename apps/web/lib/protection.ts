import type { Schemas } from "./api";
import { v1 } from "./v1";

export type Protection = Schemas["Protection"];
export type ProtectionState = Schemas["ProtectionState"];
export type ProtectionRule = Schemas["ProtectionRule"];
export type RuleMode = "native" | "check" | "inactive";

export async function protectionOf(projectId: string, appId: string): Promise<Protection | null> {
  return v1.protection(projectId, appId).catch(() => null);
}

export async function protectionDefaultOf(): Promise<boolean | null> {
  return v1.protectionDefault().then((d) => d.enforce).catch(() => null);
}
