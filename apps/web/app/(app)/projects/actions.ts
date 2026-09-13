"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { createProject, deleteProject } from "@/lib/projects";
import { requirePermission } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { assignProjectTeam } from "@/lib/teams";

export async function newProject(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  const { session, org } = await requireOrg();
  try {
    await requirePermission(session.user.id, org.id, "project.manage");
  } catch (e) {
    return { error: (e as Error).message };
  }
  const name = String(formData.get("name") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  if (!name) return { error: "name is required" };

  try {
    await createProject(org.id, name, description);
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/projects");
  return { error: undefined };
}

export async function removeProject(id: string) {
  const { session, org } = await requireOrg();
  await requirePermission(session.user.id, org.id, "project.manage");
  const registryIds = await deleteProject(org.id, id);
  await Promise.allSettled(registryIds.map((r) => api.apps.remove(r)));
  revalidatePath("/projects");
}

export async function assignTeam(projectId: string, teamId: string | null): Promise<{ ok: true } | { ok: false; error: string }> {
  const { session, org } = await requireOrg();
  try {
    await requirePermission(session.user.id, org.id, "project.manage");
    await assignProjectTeam(org.id, projectId, teamId);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  revalidatePath("/projects");
  revalidatePath("/teams");
  return { ok: true };
}
