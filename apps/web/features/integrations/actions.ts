"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { sessionCookie } from "@/lib/auth";
import { authApi } from "@/lib/auth-api";
import { type Role, ROLES } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { HOST_KINDS, type HostKind } from "@/lib/source-hosts";
import { v1 } from "@/lib/v1";

export async function createHost(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  await requireOrg();
  const kind = String(formData.get("kind") ?? "") as HostKind;
  if (!HOST_KINDS.some((k) => k.id === kind)) return { error: "unknown host kind" };
  const token = String(formData.get("token") ?? "").trim();
  if (!token) return { error: "token is required" };

  try {
    await v1.addHost({
      kind,
      name: String(formData.get("name") ?? "").trim(),
      base_url: String(formData.get("baseUrl") ?? "").trim(),
      username: String(formData.get("username") ?? "").trim(),
      token,
      default_owner: String(formData.get("defaultOwner") ?? "").trim(),
    });
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/", "layout");
  return { error: undefined };
}


export async function deleteHost(id: string) {
  await requireOrg();
  await v1.removeHost(id);
  revalidatePath("/", "layout");
}


export async function rotateHostToken(id: string, token: string): Promise<{ error?: string } | null> {
  await requireOrg();
  if (!token.trim()) return { error: "token is required" };
  try {
    await v1.rotateHostToken(id, token.trim());
  } catch (e) {
    return { error: (e as Error).message };
  }
  revalidatePath("/", "layout");
  return null;
}


export async function changeHostOwner(id: string, owner: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.setHostOwner(id, owner);
    revalidatePath("/", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}


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
