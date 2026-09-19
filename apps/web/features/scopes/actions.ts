"use server";

import { failed, type Result } from "@/lib/result";
import { refreshProject } from "@/lib/revalidate";
import type { ScopeRequest, Scopes } from "@/lib/scopes";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function createScope(projectId: string, appId: string, body: ScopeRequest): Promise<Result<Scopes>> {
  await requireOrg();
  try {
    const data = await v1.createScope(projectId, appId, body);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function updateScope(projectId: string, appId: string, name: string, body: ScopeRequest): Promise<Result<Scopes>> {
  await requireOrg();
  try {
    const data = await v1.updateScope(projectId, appId, name, body);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function deleteScope(projectId: string, appId: string, name: string): Promise<Result<Scopes>> {
  await requireOrg();
  try {
    const data = await v1.deleteScope(projectId, appId, name);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}
