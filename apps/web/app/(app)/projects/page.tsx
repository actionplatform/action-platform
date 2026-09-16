import { Download } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { projectsOf } from "@/lib/projects";


import { requireOrg } from "@/lib/session";
import { teamsOf } from "@/lib/teams";
import { LiveList } from "@/features/projects";
import { NewProjectForm } from "@/features/projects";
import { ProjectsView } from "@/features/projects";

export default async function ProjectsPage() {
  const { session, org } = await requireOrg();
  const [projects, teams] = await Promise.all([projectsOf(org.id), teamsOf(org.id)]);
  const manage = !!session.grants["project.manage"];

  return (
    <>
      <PageHeader title="Projects" description="Manage your projects and the apps that ship together." shortDescription="Manage the apps you ship." actions={manage ? <div className="grid grid-cols-1 gap-2 min-[340px]:grid-cols-[1fr_1.25fr] md:flex md:items-center"><Link href="/import" className="min-w-0"><Button size="lg" variant="outline" className="h-12 w-full whitespace-nowrap md:h-[42px] md:w-auto"><Download className="size-4" strokeWidth={2} /> Import</Button></Link><NewProjectForm /></div> : undefined} />
      <LiveList active={projects.some((p) => p.tearingDown)} />
      <ProjectsView
        projects={projects.map((p) => ({ id: p.id, name: p.name, slug: p.slug, description: p.description, apps: p.apps, teamId: p.teamId, teamName: p.teamName, updatedAt: p.updatedAt, tearingDown: p.tearingDown }))}
        teams={teams.map((t) => ({ id: t.id, name: t.name }))}
        canManage={manage}
      />
    </>
  );
}
