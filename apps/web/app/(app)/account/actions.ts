"use server";

import { revalidatePath } from "next/cache";
import { revokeToken } from "@/lib/api-tokens";
import { failed, type Result } from "@/lib/result";
import { requireSession } from "@/lib/session";
import { revokeSession } from "@/lib/sessions";

export async function revokeApiToken(id: string): Promise<Result> {
  try {
    await requireSession();
    if (!(await revokeToken(id))) return { ok: false, error: "token not found" };
    revalidatePath("/account");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function revokeBrowserSession(id: string): Promise<Result> {
  try {
    await requireSession();
    if (!(await revokeSession(id))) return { ok: false, error: "session not found" };
    revalidatePath("/account");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
