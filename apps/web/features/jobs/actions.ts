"use server";

import type { Schemas } from "@/lib/api";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export type JobLogPage = Schemas["JobLogsOut"];

export async function jobLogs(id: string, after = 0): Promise<Result<JobLogPage>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.jobLogs(id, after) };
  } catch (e) {
    return failed(e);
  }
}
