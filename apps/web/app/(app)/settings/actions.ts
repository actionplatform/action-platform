"use server";

import { revalidatePath } from "next/cache";
import { requireOrg } from "@/lib/session";
import { addHost, HOST_KINDS, type HostKind, removeHost, updateHostToken } from "@/lib/source-hosts";

export async function createHost(_prev: { error?: string } | null, formData: FormData): Promise<{ error?: string } | null> {
  const { org } = await requireOrg();
  const kind = String(formData.get("kind") ?? "") as HostKind;
  if (!HOST_KINDS.some((k) => k.id === kind)) return { error: "unknown host kind" };
  const token = String(formData.get("token") ?? "").trim();
  if (!token) return { error: "token is required" };

  try {
    await addHost(org.id, {
      kind,
      name: String(formData.get("name") ?? "").trim() || HOST_KINDS.find((k) => k.id === kind)!.label,
      baseUrl: String(formData.get("baseUrl") ?? "").trim(),
      username: String(formData.get("username") ?? "").trim(),
      token,
      defaultOwner: String(formData.get("defaultOwner") ?? "").trim(),
    });
  } catch (e) {
    return { error: (e as Error).message };
  }

  revalidatePath("/settings");
  return { error: undefined };
}

export async function deleteHost(id: string) {
  const { org } = await requireOrg();
  await removeHost(org.id, id);
  revalidatePath("/settings");
}

export async function rotateHostToken(id: string, token: string): Promise<{ error?: string } | null> {
  const { org } = await requireOrg();
  if (!token.trim()) return { error: "token is required" };
  await updateHostToken(org.id, id, token.trim());
  revalidatePath("/settings");
  return null;
}
