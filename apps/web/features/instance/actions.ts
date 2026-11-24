"use server";

import type { Schemas } from "@/lib/api";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export type TestEmail = Schemas["TestEmailOut"];

export async function sendTestEmail(): Promise<Result<TestEmail>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.sendTestEmail() };
  } catch (e) {
    return failed(e);
  }
}
