"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import type { Schemas } from "@/lib/api";
import { v1 } from "@/lib/v1";

export type GithubOrganization = Schemas["GithubOrganization"];
export type GithubOrganizations = Schemas["GithubOrganizations"];
export type GithubPreview = Schemas["GithubPreview"];
export type ImportSummary = { projects: string[]; apps: string[]; teams: string[]; members: string[]; invitations: string[]; skipped: string[] };

export async function loadGithubOrganizations(host: string): Promise<Result<GithubOrganizations>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.githubOrganizations(host) };
  } catch (e) {
    return failed(e);
  }
}

export async function loadGithubOrganization(host: string, login: string): Promise<Result<GithubPreview>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.githubOrganization(host, login) };
  } catch (e) {
    return failed(e);
  }
}

export async function startGithubImport(body: Schemas["ImportRequest"]): Promise<Result<{ job: string }>> {
  await requireOrg();
  try {
    return { ok: true, data: await v1.importGithub(body) };
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
      revalidatePath("/teams");
      revalidatePath("/settings", "layout");
    }
    return { ok: true, data: { status: job.status, result: (job.result as ImportSummary | null) ?? null, error: job.error ?? null } };
  } catch (e) {
    return failed(e);
  }
}
