"use server";

import { revalidatePath } from "next/cache";
import { api, type InitRequest } from "@/lib/api";
import { createApp, projectById } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { credentialsFor } from "@/lib/source-hosts";

export async function createAppFromTemplate(projectId: string, sourceHostId: string | null, body: InitRequest): Promise<{ ok: true; href: string } | { ok: false; error: string }> {
  const { org } = await requireOrg();
  const project = await projectById(org.id, projectId);
  if (!project) return { ok: false, error: "project not found" };

  try {
    const credentials = sourceHostId ? await credentialsFor(org.id, sourceHostId) : null;
    if (body.push && !credentials) return { ok: false, error: "pushing needs a source host" };
    const result = await api.apps.init({ ...body, credentials });
    const app = await createApp(project.id, result.id, result.name, sourceHostId);
    revalidatePath(`/projects/${project.id}`);
    return { ok: true, href: `/projects/${project.id}/apps/${app.id}` };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}
