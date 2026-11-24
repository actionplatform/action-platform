"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import type { Schemas } from "@/lib/api";
import { v1 } from "@/lib/v1";

export type ImportOrganization = Schemas["ImportOrganization"];
export type ImportOrganizations = Schemas["ImportOrganizations"];
export type ImportPreview = Schemas["ImportPreview"];
export type ImportSummary = { projects: string[]; apps: string[]; teams: string[]; members: string[]; invitations: string[]; login_invitations?: string[]; waiting?: string[]; skipped: string[] };

export async function loadOrganizations(host: string): Promise<Result<ImportOrganizations>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.importOrganizations(host) };
  } catch (e) {
    return failed(e);
  }
}

export async function loadPreview(host: string, login: string): Promise<Result<ImportPreview>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.importPreview(host, login) };
  } catch (e) {
    return failed(e);
  }
}

export async function startImport(body: Schemas["ImportRequest"]): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.importOrganization(body) };
  } catch (e) {
    return failed(e);
  }
}

export async function importJob(id: string): Promise<Result<{ status: string; result: ImportSummary | null; error: string | null }>> {
  await requireOrg();
  try {
    const job = await v1.job(id);
    if (job.status === "done") {
      revalidatePath("/projects");
      revalidatePath("/", "layout");
      revalidatePath("/", "layout");
    }
    return { ok: true, data: { status: job.status, result: (job.result as ImportSummary | null) ?? null, error: job.error ?? null } };
  } catch (e) {
    return failed(e);
  }
}
