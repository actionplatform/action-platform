import { ArrowUpRight, FolderKanban } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { projectsOf } from "@/lib/projects";
import { requireOrg } from "@/lib/session";
import { NewProjectForm } from "./new-project-form";
import { RemoveProjectButton } from "./remove-project-button";

export default async function ProjectsPage() {
  const { org } = await requireOrg();
  const projects = await projectsOf(org.id);

  return (
    <>
      <PageHeader title="Projects" description={`Projects in ${org.name}. A project groups the apps that ship together.`} actions={<NewProjectForm />} />

      {projects.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-10 text-center">
          <FolderKanban className="mx-auto size-6 text-muted-foreground" />
          <div className="mt-3 text-sm font-medium">No projects yet</div>
          <div className="text-sm text-secondary">Create one, then add apps to it from a template or an existing repository.</div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <div key={p.id} className="group relative flex flex-col rounded-lg border border-border bg-surface p-4 transition-colors hover:border-border-hover hover:bg-surface-hover">
              <Link href={`/projects/${p.id}`} className="absolute inset-0 rounded-lg focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground" aria-label={p.name} />
              <div className="flex items-start justify-between gap-3">
                <FolderKanban className="size-5 shrink-0" />
                <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
              </div>
              <div className="mt-3 font-medium">{p.name}</div>
              <div className="font-mono text-xs text-muted-foreground">{p.slug}</div>
              {p.description && <p className="mt-1 text-sm text-secondary line-clamp-2">{p.description}</p>}
              <div className="mt-auto flex items-center justify-between pt-3">
                <Badge>{p.apps} {p.apps === 1 ? "app" : "apps"}</Badge>
                <span className="relative"><RemoveProjectButton id={p.id} name={p.name} /></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
