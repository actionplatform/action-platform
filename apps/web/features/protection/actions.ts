"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import type { Protection } from "@/lib/protection";
import { refreshProject } from "@/lib/revalidate";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function setProtection(projectId: string, appId: string, enforce: boolean | null): Promise<Result<Protection>> {
  await requireOrg();
  try {
    const data = await v1.setProtection(projectId, appId, enforce);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function applyProtection(projectId: string, appId: string): Promise<Result<Protection>> {
  await requireOrg();
  try {
    const data = await v1.applyProtection(projectId, appId);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function checkProtection(projectId: string, appId: string): Promise<Result<Protection>> {
  await requireOrg();
  try {
    const data = await v1.protection(projectId, appId, true);
    refreshProject(projectId);
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

export async function setProtectionDefault(enforce: boolean): Promise<Result<boolean>> {
  await requireOrg();
  try {
    const data = await v1.setProtectionDefault(enforce);
    revalidatePath("/", "layout");
    return { ok: true, data: data.enforce };
  } catch (e) {
    return failed(e);
  }
}
