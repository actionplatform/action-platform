"use server";

import { failed } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { api, type InitRequest } from "@/lib/api";
import { createApp, projectById } from "@/lib/projects";
import { requirePermission } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { syncReleases } from "@/lib/releases";
import { credentialsFor } from "@/lib/source-hosts";
import { sourceSpecByName } from "@/lib/template-sources";

export async function createAppFromTemplate(projectId: string, sourceHostId: string | null, body: InitRequest, templateSource: string | null = null): Promise<{ ok: true; href: string } | { ok: false; error: string }> {
  const { session, org } = await requireOrg();
  try {
    await requirePermission(session.user.id, org.id, "project.manage");
  } catch (e) {
    return failed(e);
  }
  const project = await projectById(org.id, projectId);
  if (!project) return { ok: false, error: "project not found" };

  try {
    const credentials = sourceHostId ? await credentialsFor(org.id, sourceHostId) : null;
    if (body.push && !credentials) return { ok: false, error: "pushing needs a source host" };
    const result = await api.apps.init({ ...body, credentials, source: await sourceSpecByName(org.id, templateSource) });
    const app = await createApp(project.id, result.id, result.name, sourceHostId);
    if (result.pushed && sourceHostId) await syncReleases(org.id, app.id, sourceHostId, (await api.apps.get(result.id)).source_host.repo ?? null);
    revalidatePath(`/projects/${project.id}`);
    return { ok: true, href: `/projects/${project.id}/apps/${app.id}` };
  } catch (e) {
    return failed(e);
  }
}
