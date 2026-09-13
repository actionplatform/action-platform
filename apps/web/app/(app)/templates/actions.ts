"use server";

import { revalidatePath } from "next/cache";
import { requireManager } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { addTemplateSource, removeTemplateSource } from "@/lib/template-sources";

type Result<T = null> = { ok: true; data: T } | { ok: false; error: string };

export async function addSource(input: { name: string; url: string; ref: string }): Promise<Result<{ id: string }>> {
  const { session, org } = await requireOrg();
  try {
    await requireManager(session.user.id, org.id);
    const row = await addTemplateSource(org.id, input);
    revalidatePath("/templates");
    return { ok: true, data: { id: row.id } };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
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
    return { ok: false, error: (e as Error).message };
  }
}
