"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function installPlugin(slug: string): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    const queued = await v1.installPlugin(slug);
    return { ok: true, data: { job: queued.job } };
  } catch (e) {
    return failed(e);
  }
}

export async function removePlugin(slug: string): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    const queued = await v1.removePlugin(slug);
    return { ok: true, data: { job: queued.job } };
  } catch (e) {
    return failed(e);
  }
}

export async function setPluginEnabled(slug: string, enabled: boolean): Promise<Result<null>> {
  await requireOrg();
  try {
    if (enabled) await v1.enablePlugin(slug); else await v1.disablePlugin(slug);
    revalidatePath("/plugins");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function restartPlatform(): Promise<Result<null>> {
  await requireOrg();
  try {
    await v1.restartPlatform();
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function pluginJob(id: string): Promise<Result<{ status: string; error: string | null }>> {
  await requireOrg();
  try {
    const job = await v1.job(id);
    if (job.status === "done" || job.status === "failed") revalidatePath("/plugins");
    return { ok: true, data: { status: job.status, error: job.error ?? null } };
  } catch (e) {
    return failed(e);
  }
}
