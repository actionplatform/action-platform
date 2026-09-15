"use server";

import { revalidatePath } from "next/cache";
import { failed, type Result } from "@/lib/result";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

export async function savePluginOptions(slug: string, values: Record<string, unknown>): Promise<Result<null>> {
  const { session } = await requireOrg();
  if (!session.grants["org.manage"]) return { ok: false, error: "Only org.manage can change integrations." };
  const options: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) options[key] = trimmed;
    } else if (value !== undefined && value !== null) {
      options[key] = value;
    }
  }
  try {
    await v1.setPluginOptions(slug, options);
    revalidatePath("/", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
