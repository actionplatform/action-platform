"use server";

import { failed, type Result } from "@/lib/result";
import { revalidatePath } from "next/cache";
import { requireOrg } from "@/lib/session";
import { v1 } from "@/lib/v1";

function refresh(teamId?: string) {
  revalidatePath("/teams");
  revalidatePath("/projects");
  if (teamId) revalidatePath(`/teams/${teamId}`);
}

export async function newTeam(name: string, description: string): Promise<Result<{ id: string }>> {
  try {
    await requireOrg();
    const team = await v1.createTeam(name, description);
    refresh();
    return { ok: true, data: { id: team.id } };
  } catch (e) {
    return failed(e);
  }
}

export async function editTeam(teamId: string, name: string, description: string): Promise<Result> {
  try {
    await requireOrg();
    await v1.updateTeam(teamId, name, description);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function removeTeam(teamId: string): Promise<Result> {
  try {
    await requireOrg();
    await v1.deleteTeam(teamId);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function addMemberToTeam(teamId: string, userId: string): Promise<Result> {
  try {
    await requireOrg();
    await v1.addTeamMember(teamId, userId);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function removeMemberFromTeam(teamId: string, userId: string): Promise<Result> {
  try {
    await requireOrg();
    await v1.removeTeamMember(teamId, userId);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}

export async function setProjectTeam(teamId: string, projectId: string, assign: boolean): Promise<Result> {
  try {
    await requireOrg();
    await v1.assignProjectTeam(projectId, assign ? teamId : null);
    refresh(teamId);
    return { ok: true, data: null };
  } catch (e) {
    return failed(e);
  }
}
