import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/layout/page";
import { projectById } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { teamsOf } from "@/lib/teams";
import { ProjectSettings } from "@/features/projects";

export default async function ProjectSettingsPage({ params }: { params: Promise<{ project: string }> }) {
  const { project: projectId } = await params;
  const { session, org } = await requireOrg();
  if (!session.grants["project.manage"]) notFound();
  const [project, teams] = await Promise.all([projectById(org.id, projectId), teamsOf(org.id)]);
  if (!project) notFound();

  return (
    <>
      <div className="mb-4 text-xs text-secondary">
        <Link href="/projects" className="hover:text-foreground">Projects</Link>
        {" / "}<Link href={`/projects/${project.id}`} className="hover:text-foreground">{project.name}</Link>
        {" / "}<span className="text-foreground">Settings</span>
      </div>
      <PageHeader title={`Settings · ${project.name}`} description="Who looks after this project, and removing it." />
      <ProjectSettings project={{ id: project.id, name: project.name, teamId: project.teamId, apps: project.apps }} teamName={project.teamName} teams={teams.map((t) => ({ id: t.id, name: t.name }))} />
    </>
  );
}
