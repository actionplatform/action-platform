"use server";

import { revalidatePath } from "next/cache";
import { createOrg } from "@/lib/orgs";
import { requireSession } from "@/lib/session";

export async function createOrganization(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  await requireSession();
  const name = String(formData.get("name") ?? "").trim();
  const slug = String(formData.get("slug") ?? "").trim();
  if (!name) return { error: "name is required" };

  try {
    await createOrg(name, slug || undefined);
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/", "layout");
  return { error: undefined };
}
