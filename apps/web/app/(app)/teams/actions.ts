"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { requireManager } from "@/lib/orgs";
import { requireOrg } from "@/lib/session";
import { addTeamMember, assignProjectTeam, createTeam, deleteTeam, removeTeamMember, updateTeam } from "@/lib/teams";


async function manager() {
  const { session, org } = await requireOrg();
  await requireManager(session.user.id, org.id);
  return org;
}

function refresh(teamId?: string) {
  revalidatePath("/teams");
  revalidatePath("/projects");
  if (teamId) revalidatePath(`/teams/${teamId}`);
}

export async function newTeam(name: string, description: string): Promise<Result<{ id: string }>> {
  try {
    const org = await manager();
    const team = await createTeam(org.id, name, description);
    refresh();
    return { ok: true, data: { id: team.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function editTeam(teamId: string, name: string, description: string): Promise<Result> {
  try {
    const org = await manager();
    await updateTeam(org.id, teamId, name, description);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function removeTeam(teamId: string): Promise<Result> {
  try {
    const org = await manager();
    await deleteTeam(org.id, teamId);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function addMemberToTeam(teamId: string, userId: string): Promise<Result> {
  try {
    const org = await manager();
    await addTeamMember(org.id, teamId, userId);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function removeMemberFromTeam(teamId: string, id: string): Promise<Result> {
  try {
    const org = await manager();
    await removeTeamMember(org.id, teamId, id);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function setProjectTeam(teamId: string, projectId: string, assign: boolean): Promise<Result> {
  try {
    const org = await manager();
    await assignProjectTeam(org.id, projectId, assign ? teamId : null);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
