"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";

export async function addProject(formData: FormData) {
  const path = String(formData.get("path") ?? "").trim();
  if (!path) return;
  await api.projects.add(path);
  revalidatePath("/projects");
}

export async function removeProject(id: string) {
  await api.projects.remove(id);
  revalidatePath("/projects");
}

export async function previewRelease(id: string, level: string) {
  return api.projects.release(id, level, true);
}

export async function runRelease(id: string, level: string) {
  const result = await api.projects.release(id, level, false);
  revalidatePath(`/projects/${id}`);
  return result;
}

export async function previewDeploy(id: string, stage: string | null) {
  return api.projects.deploy(id, stage, true);
}

export async function runDeploy(id: string, stage: string | null) {
  const result = await api.projects.deploy(id, stage, false);
  revalidatePath(`/projects/${id}`);
  return result;
}
