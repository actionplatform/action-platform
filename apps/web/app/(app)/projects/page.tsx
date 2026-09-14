import { PageHeader } from "@/components/layout/page";
import { projectsOf } from "@/lib/projects";


import { requireOrg } from "@/lib/session";
import { teamsOf } from "@/lib/teams";
import { NewProjectForm } from "./new-project-form";
import { ProjectsView } from "./projects-view";

export default async function ProjectsPage() {
  const { session, org } = await requireOrg();
  const [projects, teams] = await Promise.all([projectsOf(org.id), teamsOf(org.id)]);
  const manage = !!session.grants["project.manage"];

  return (
    <>
      <PageHeader title="Projects" description="Manage your projects and the apps that ship together." actions={manage ? <NewProjectForm /> : undefined} />
      <ProjectsView
        projects={projects.map((p) => ({ id: p.id, name: p.name, slug: p.slug, description: p.description, apps: p.apps, teamId: p.teamId, teamName: p.teamName, updatedAt: p.updatedAt }))}
        teams={teams.map((t) => ({ id: t.id, name: t.name }))}
        canManage={manage}
      />
    </>
  );
}
