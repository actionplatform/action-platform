import { notFound } from "next/navigation";
import { PageHeader } from "@/components/layout/page";
import { membersOf } from "@/lib/orgs";
import { projectsOf } from "@/lib/projects";
import { can } from "@/lib/permissions";
import { requireOrg } from "@/lib/session";
import { projectsOfTeam, teamById, teamMembersOf } from "@/lib/teams";
import { TeamDetail } from "./team-detail";

export const dynamic = "force-dynamic";

export default async function TeamPage({ params }: { params: Promise<{ team: string }> }) {
  const { team: teamId } = await params;
  const { session, org } = await requireOrg();
  const team = await teamById(org.id, teamId);
  if (!team) notFound();

  const [members, orgMembers, projects, allProjects, role] = await Promise.all([teamMembersOf(team.id), membersOf(org.id), projectsOfTeam(org.id, team.id), projectsOf(org.id), Promise.resolve(session.role)]);
  const canManage = can(role, "org.manage");
  const inTeam = new Set(members.map((m) => m.userId));

  return (
    <>
      <PageHeader title={team.name} description={team.description || `${org.name} team.`} />
      <TeamDetail
        team={{ id: team.id, name: team.name, description: team.description ?? "" }}
        members={members.map((m) => ({ id: m.id, userId: m.userId, name: m.name, email: m.email }))}
        candidates={orgMembers.filter((m) => !inTeam.has(m.userId)).map((m) => ({ userId: m.userId, name: m.name, email: m.email }))}
        projects={projects.map((p) => ({ id: p.id, name: p.name, slug: "", description: null }))}
        candidatesProjects={allProjects.filter((p) => p.teamId !== team.id).map((p) => ({ id: p.id, name: p.name, teamName: p.teamName }))}
        canManage={canManage}
      />
    </>
  );
}
