"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { createProject, deleteProject } from "@/lib/projects";
import { requireOrg } from "@/lib/session";

export async function newProject(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  const { org } = await requireOrg();
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
  const { org } = await requireOrg();
  const registryIds = await deleteProject(org.id, id);
  await Promise.allSettled(registryIds.map((r) => api.apps.remove(r)));
  revalidatePath("/projects");
}
