"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function addSource(input: { name: string; url: string; ref: string }): Promise<Result<{ id: string }>> {
  await requireOrg();
  try {
    const row = await v1.addTemplateSource(input.name, input.url, input.ref);
    revalidatePath("/templates");
    return { ok: true, data: { id: row.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function removeSource(id: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.removeTemplateSource(id);
    revalidatePath("/templates");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
