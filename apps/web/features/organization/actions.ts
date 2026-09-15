"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { sessionCookie } from "@/lib/auth";
import { authApi } from "@/lib/auth-api";
import { type Role, ROLES } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { HOST_KINDS, type HostKind } from "@/lib/source-hosts";
import { v1 } from "@/lib/v1";

export async function inviteMember(email: string, role: Role): Promise<Result<{ id: string }>> {
  await requireOrg();
  try {
    if (!ROLES.includes(role)) throw new Error("unknown role");
    const invitation = await v1.invite(email, role);
    revalidatePath("/", "layout");
    return { ok: true, data: { id: invitation.id } };
  } catch (e) {
    return failed(e);
  }
}


export async function revokeInvitation(id: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.cancelInvitation(id);
    revalidatePath("/", "layout");
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
    revalidatePath("/", "layout");
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}


export async function kickMember(userId: string): Promise<Result> {
  await requireOrg();
  try {
    await v1.removeMember(userId);
    revalidatePath("/", "layout");
    revalidatePath("/", "layout");
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
    revalidatePath("/", "layout");
    revalidatePath("/", "layout");
    return { ok: true, data: { existed: added.existed } };
  } catch (e) {
    return failed(e);
  }
}


export async function saveGitAuthor(author: { name: string; email: string }): Promise<Result<{ name: string; email: string }>> {
  await requireOrg();
  try {
    const data = await v1.setGitAuthor(author.name, author.email);
    revalidatePath("/", "layout");
    return { ok: true, data };
  } catch (e) {
    return failed(e);
  }
}

