import { type TeamRow, v1 } from "./v1";

export type Team = { id: string; organizationId: string; name: string; slug: string; description: string | null; members: number; projects: number };
export type TeamMember = { id: string; userId: string; name: string; email: string };
export type TeamProject = { id: string; name: string };

function team(row: TeamRow, orgId: string): Team {
  return { id: row.id, organizationId: orgId, name: row.name, slug: row.slug, description: row.description ?? null, members: row.members.length, projects: row.projects.length };
}

export async function teamsOf(orgId: string): Promise<Team[]> {
  return (await v1.teams()).map((r) => team(r, orgId));
}

export async function teamById(orgId: string, id: string): Promise<Team | null> {
  const row = (await v1.teams()).find((t) => t.id === id);
  return row ? team(row, orgId) : null;
}

export async function teamMembersOf(teamId: string): Promise<TeamMember[]> {
  const row = (await v1.teams()).find((t) => t.id === teamId);
  return (row?.members ?? []).map((m) => ({ id: m.userId, userId: m.userId, name: m.name, email: m.email }));
}

export async function projectsOfTeam(_orgId: string, teamId: string): Promise<TeamProject[]> {
  const row = (await v1.teams()).find((t) => t.id === teamId);
  return row?.projects ?? [];
}
