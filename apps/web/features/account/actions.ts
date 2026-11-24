"use server";

import { revalidatePath } from "next/cache";
import { requestClient, sessionCookie } from "@/lib/auth";
import { authApi, isAuthError } from "@/lib/auth-api";
import { issueUserToken, revokeToken } from "@/lib/api-tokens";
import type { NewToken } from "@/lib/new-token";
import { failed, type Result } from "@/lib/result";
import { requireSession } from "@/lib/session";
import { revokeSession } from "@/lib/sessions";

export async function revokeApiToken(id: string): Promise<Result> {
  try {
    await requireSession();
    if (!(await revokeToken(id))) return { ok: false, error: "token not found" };
    revalidatePath("/organization/sessions");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function revokeBrowserSession(id: string): Promise<Result> {
  try {
    await requireSession();
    if (!(await revokeSession(id))) return { ok: false, error: "session not found" };
    revalidatePath("/organization/sessions");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function createApiToken(input: NewToken): Promise<Result<{ token: string; scope: string[]; expiresAt: number }>> {
  try {
    await requireSession();
    if (!input.name.trim()) return { ok: false, error: "name the token" };
    const issued = await issueUserToken(input);
    revalidatePath("/organization/sessions");
    return { ok: true, data: { token: issued.token, scope: issued.scope, expiresAt: issued.expiresAt.getTime() } };
  } catch (e) {
    return failed(e);
  }
}

export async function changePassword(current: string, next: string): Promise<Result> {
  try {
    await requireSession();
    const cookie = await sessionCookie();
    if (!cookie) return { ok: false, error: "sign in first" };
    const { ip } = await requestClient();
    await authApi.changePassword({ cookie }, { current_password: current, new_password: next }, ip);
    revalidatePath("/organization/sessions");
    return { ok: true, data: null };
  } catch (e) {
    if (isAuthError(e, 429)) return { ok: false, error: "too many attempts, wait a minute" };
    return failed(e);
  }
}
