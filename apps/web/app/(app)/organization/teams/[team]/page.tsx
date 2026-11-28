import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { membersOf } from "@/lib/orgs";
import { projectsOf } from "@/lib/projects";

import { pageQuery, paginate } from "@/lib/page";
import { requireOrg } from "@/lib/session";
import { projectsOfTeam, teamById, teamMembersOf } from "@/lib/teams";
import { TeamDetail } from "@/features/organization";

export const dynamic = "force-dynamic";

export default async function TeamPage({ params, searchParams }: { params: Promise<{ team: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { team: teamId } = await params;
  const query = pageQuery(await searchParams, "members");
  const { session, org } = await requireOrg();
  const team = await teamById(org.id, teamId);
  if (!team) notFound();

  const [members, orgMembers, projects, allProjects] = await Promise.all([teamMembersOf(team.id), membersOf(), projectsOfTeam(org.id, team.id), projectsOf(org.id)]);
  const canManage = !!session.grants["org.manage"];
  const inTeam = new Set(members.map((m) => m.userId));

  return (
    <>
      <div className="mb-5">
        <Link href="/organization/teams" className="inline-flex items-center gap-1.5 text-sm text-secondary hover:text-foreground"><ArrowLeft className="size-3.5" strokeWidth={1.75} /> Teams</Link>
        <h2 className="mt-2 text-[18px] font-semibold">{team.name}</h2>
        <p className="text-sm text-secondary">{team.description || `${org.name} team.`}</p>
      </div>
      <TeamDetail
        team={{ id: team.id, name: team.name, description: team.description ?? "" }}
        members={paginate(members, query).items.map((m) => ({ id: m.id, userId: m.userId, name: m.name, email: m.email }))}
        membersPaging={{ total: members.length, page: query.page, per: query.per }}
        candidates={orgMembers.filter((m) => !inTeam.has(m.userId)).map((m) => ({ userId: m.userId, name: m.name, email: m.email }))}
        projects={projects.map((p) => ({ id: p.id, name: p.name, slug: "", description: null }))}
        candidatesProjects={allProjects.filter((p) => p.teamId !== team.id).map((p) => ({ id: p.id, name: p.name, teamName: p.teamName }))}
        canManage={canManage}
      />
    </>
  );
}
