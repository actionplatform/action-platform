"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import { api, ApiError, type DeployResult, type ReleasePreview } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function startBranch(projectId: string, _appId: string, registryId: string, input: { kind: string; code: string; slug: string; push: boolean }): Promise<Result<{ branch: string; base: string; pushed: boolean }>> {
  await requireOrg();
  try {
    const data = await api.apps.startBranch(registryId, { ...input, slug: input.slug || null });
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function planBranch(registryId: string, kind: string, code: string, slug: string): Promise<Result<{ branch: string; base: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.planBranch(registryId, kind, code, slug || null);
    return { ok: true, data: { branch: data.branch, base: data.base } };
  } catch (e) {
    return failed(e);
  }
}


export async function checkoutBranch(projectId: string, registryId: string, branch: string): Promise<Result<{ branch: string }>> {
  await requireOrg();
  try {
    const data = (await api.apps.checkout(registryId, branch)) as { branch: string };
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}


export async function proposePullRequest(_projectId: string, registryId: string): Promise<Result<{ head: string; base: string; title: string; body: string; commits: string[] }>> {
  await requireOrg();
  try {
    return { ok: true, data: await api.apps.proposePullRequest(registryId) };
  } catch (e) {
    return failed(e);
  }
}


export async function openPullRequest(projectId: string, _appId: string, registryId: string, input: { base: string; title: string; body: string; draft: boolean }): Promise<Result<{ number: number; url: string }>> {
  await requireOrg();
  try {
    const data = await api.apps.openPullRequest(registryId, input);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

