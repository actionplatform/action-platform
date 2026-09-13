"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { requireManager } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { addTemplateSource, removeTemplateSource } from "@/lib/template-sources";


export async function addSource(input: { name: string; url: string; ref: string }): Promise<Result<{ id: string }>> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    const row = await addTemplateSource(org.id, input);
    revalidatePath("/templates");
    return { ok: true, data: { id: row.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function removeSource(id: string): Promise<Result> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    await removeTemplateSource(org.id, id);
    revalidatePath("/templates");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
