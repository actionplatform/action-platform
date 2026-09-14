"use server";

import { failed } from "@/lib/result";
import { revalidatePath } from "next/cache";
import type { InitRequest } from "@/lib/api";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function createAppFromTemplate(projectId: string, sourceHostId: string | null, body: InitRequest, templateSource: string | null = null): Promise<{ ok: true; href: string } | { ok: false; error: string }> {
  await requireOrg();
  try {
    const app = await v1.initApp(projectId, { ...body, credentials: null, source: null, source_host_id: sourceHostId, template_source: templateSource });
    revalidatePath(`/projects/${projectId}`);
    return { ok: true, href: `/projects/${projectId}/apps/${app.id}` };
  } catch (e) {
    return failed(e);
  }
}
