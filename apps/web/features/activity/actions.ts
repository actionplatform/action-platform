"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api } from "@/lib/api";
import { requireOrg } from "@/lib/session";

export async function startBranch(projectId: string, _appId: string, registryId: string, input: { kind: string; code: string; slug: string; push: boolean }): Promise<Result<{ branch: string; base: string; pushed: boolean }>> {
  await requireOrg();
  try {
    const data = await api.apps.startBranch(projectId, registryId, { ...input, slug: input.slug || null });
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function planBranch(projectId: string, registryId: string, kind: string, code: string, slug: string): Promise<Result<{ branch: string; base: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.planBranch(projectId, registryId, kind, code, slug || null);
    return { ok: true, data: { branch: data.branch, base: data.base } };
  } catch (e) {
    return failed(e);
  }
}


export async function checkoutBranch(projectId: string, registryId: string, branch: string): Promise<Result<{ branch: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.checkout(projectId, registryId, branch)) as { branch: string };
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function proposePullRequest(projectId: string, registryId: string): Promise<Result<{ head: string; base: string; title: string; body: string; commits: string[] }>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.proposePullRequest(projectId, registryId) };
  } catch (e) {
    return failed(e);
  }
}


export async function openPullRequest(projectId: string, _appId: string, registryId: string, input: { base: string; title: string; body: string; draft: boolean }): Promise<Result<{ number: number; url: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.openPullRequest(projectId, registryId, input);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

