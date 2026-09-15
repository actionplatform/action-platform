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

  revalidatePath("/settings", "layout");
  return { error: undefined };
}

export async function deleteHost(id: string) {
  await requireOrg();
  await v1.removeHost(id);
  revalidatePath("/settings", "layout");
}

export async function rotateHostToken(id: string, token: string): Promise<{ error?: string } | null> {
  await requireOrg();
  if (!token.trim()) return { error: "token is required" };
  try {
    await v1.rotateHostToken(id, token.trim());
  } catch (e) {
    return { error: (e as Error).message };
  }
  revalidatePath("/settings", "layout");
  return null;
}

export async function inviteMember(email: string, role: Role): Promise<Result<{ id: string }>> {
  await requireOrg();
  try {
    if (!ROLES.includes(role)) throw new Error("unknown role");
    const invitation = await v1.invite(email, role);
    revalidatePath("/settings", "layout");
    return { ok: true, data: { id: invitation.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function revokeInvitation(id: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.cancelInvitation(id);
    revalidatePath("/settings", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function changeRole(userId: string, role: Role): Promise<Result> {
  await requireOrg();
  try {
    if (!ROLES.includes(role)) throw new Error("unknown role");
    await v1.setMemberRole(userId, role);
    revalidatePath("/settings", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function kickMember(userId: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.removeMember(userId);
    revalidatePath("/settings", "layout");
    revalidatePath("/teams");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function addMember(input: { name: string; email: string; password: string; role: Role }): Promise<Result<{ existed: boolean }>> {
  const { org } = await requireOrg();
  try {
    if (!ROLES.includes(input.role)) throw new Error("unknown role");
    const cookie = await sessionCookie();
    if (!cookie) throw new Error("sign in first");
    const added = await authApi.addMember({ cookie }, { organization_id: org.id, name: input.name, email: input.email, password: input.password, role: input.role });
    revalidatePath("/settings", "layout");
    revalidatePath("/teams");
    return { ok: true, data: { existed: added.existed } };
  } catch (e) {
    return failed(e);
  }
}

export async function changeHostOwner(id: string, owner: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.setHostOwner(id, owner);
    revalidatePath("/settings", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function saveGitAuthor(author: { name: string; email: string }): Promise<Result<{ name: string; email: string }>> {
  await requireOrg();
  try {
    const data = await v1.setGitAuthor(author.name, author.email);
    revalidatePath("/settings", "layout");
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}
