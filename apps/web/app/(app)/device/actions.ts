"use server";

import { deviceRequest, setDeviceScope } from "@/lib/api-tokens";
import { DEFAULT_SCOPES, parseScopes, type Scope } from "@/lib/permissions";
import { failed, type Result } from "@/lib/result";
import { requireSession } from "@/lib/session";

export async function inspectDevice(userCode: string): Promise<Result<{ scope: Scope[]; clientId: string | null }>> {
  try {
    await requireSession();
    const request = await deviceRequest(userCode.trim().toUpperCase());
    if (!request || request.status !== "pending") return { ok: false, error: "invalid or expired code" };
    return { ok: true, data: { scope: request.scope.length ? request.scope : DEFAULT_SCOPES, clientId: request.clientId } };
  } catch (e) {
    return failed(e);
  }
}

export async function chooseDeviceScope(userCode: string, scope: string[]): Promise<Result<{ scope: Scope[] }>> {
  try {
    await requireSession();
    const chosen = parseScopes(scope.join(" "));
    const withRead = chosen.includes("read") ? chosen : (["read", ...chosen] as Scope[]);
    if (!(await setDeviceScope(userCode.trim().toUpperCase(), withRead))) return { ok: false, error: "invalid or expired code" };
    return { ok: true, data: { scope: withRead } };
  } catch (e) {
    return failed(e);
  }
}
