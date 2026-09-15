"use server";

import { failed } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function newProject(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  await requireOrg();
  const name = String(formData.get("name") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  if (!name) return { error: "name is required" };

  try {
    await v1.createProject(name, description);
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/projects");
  return { error: undefined };
}

export async function removeProject(id: string, repositories = false): Promise<{ ok: true } | { ok: false; error: string }> {
  await requireOrg();
  try {
    await v1.deleteProject(id, repositories);
  } catch (e) {
    return failed(e);
  }
  revalidatePath("/projects");
  return { ok: true };
}

export async function assignTeam(projectId: string, teamId: string | null): Promise<{ ok: true } | { ok: false; error: string }> {
  await requireOrg();
  try {
    await v1.assignProjectTeam(projectId, teamId);
  } catch (e) {
    return failed(e);
  }
  revalidatePath("/projects");
  revalidatePath("/settings", "layout");
  return { ok: true };
}
