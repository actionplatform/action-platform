"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { refreshProject } from "@/lib/revalidate";
import { CI_HOST_KINDS, type CiHostKind, type CiState, ciState } from "@/lib/ci";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function createCiHost(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  await requireOrg();
  const kind = String(formData.get("kind") ?? "") as CiHostKind;
  if (!CI_HOST_KINDS.some((k) => k.id === kind)) return { error: "unknown ci kind" };
  const token = String(formData.get("token") ?? "").trim();
  if (!token) return { error: "token is required" };
  const baseUrl = String(formData.get("baseUrl") ?? "").trim();
  if (!baseUrl) return { error: "base url is required" };

  try {
    await v1.addCiHost({ kind, name: String(formData.get("name") ?? "").trim(), base_url: baseUrl, username: String(formData.get("username") ?? "").trim(), token });
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/", "layout");
  return { error: undefined };
}

export async function deleteCiHost(id: string) {
  await requireOrg();
  await v1.removeCiHost(id);
  revalidatePath("/", "layout");
}

export async function testCiHost(id: string): Promise<Result<{ ok: boolean; error: string | null }>> {
  await requireOrg();
  try {
    const r = (await v1.testCiHost(id)) as { ok: boolean; error: string | null };
    return { ok: true, data: r };
  } catch (e) {
    return failed(e);
  }
}

export async function linkCi(projectId: string, appId: string, ciHostId: string | null, job: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.linkCi(projectId, appId, ciHostId, job);
    refreshProject(projectId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function syncCi(projectId: string, appId: string, page = 1, per = 10): Promise<Result<CiState>> {
  await requireOrg();
  try {
    const data = ciState(await v1.syncCi(projectId, appId, page, per));
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function startCi(projectId: string, appId: string, ref: string): Promise<Result<{ id: string; url: string | null; ref: string }>> {
  await requireOrg();
  try {
    const r = await v1.startCi(projectId, appId, ref);
    refreshProject(projectId);
    return { ok: true, data: { id: r.id, url: r.url ?? null, ref: r.ref } };
  } catch (e) {
    return failed(e);
  }
}
