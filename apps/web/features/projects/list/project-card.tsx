"use client";

import { ArrowUpRight, Clock, FolderGit2, Layers, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";
import { ProjectActionsMenu } from "./project-actions-menu";

export type ProjectItem = { id: string; name: string; slug: string; description: string | null; apps: number; teamId: string | null; teamName: string | null; updatedAt: string; tearingDown?: boolean };
export type TeamOption = { id: string; name: string };

export function ProjectCard({ project, teams, canManage }: { project: ProjectItem; teams: TeamOption[]; canManage: boolean }) {
  const router = useRouter();
  const href = `/projects/${project.id}`;
  const status = project.tearingDown ? "Tearing down" : project.apps > 0 ? "Active" : "Empty";

  return (
    <article
      tabIndex={0}
      role="link"
      aria-label={`Open ${project.name}`}
      onClick={() => router.push(href)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(href); } }}
      className="group flex cursor-pointer flex-col rounded-xl border border-border bg-surface p-4 md:h-[180px] md:rounded-[9px] md:px-6 md:py-[22px] transition-[border-color,background-color,transform] duration-150 ease-out hover:-translate-y-px hover:border-border-hover hover:bg-[#131313] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
    >
      <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 md:items-start">
        <div className="flex size-11 items-center justify-center rounded-lg border border-[#303030] md:size-12">
          <FolderGit2 className="size-[22px] text-secondary" strokeWidth={1.5} />
        </div>
        <div className="min-w-0 md:col-span-3 md:mt-4">
          <h2 className="truncate text-base font-semibold leading-6 md:text-[17px]">{project.name}</h2>
          <div className="truncate font-mono text-[13px] text-secondary">{project.slug}</div>
        </div>
        <div className="-mr-2 flex items-center md:col-start-3 md:row-start-1 md:-mr-0 md:gap-1" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
          <Link
            href={href}
            title="Open project"
            aria-label={`Open ${project.name}`}
            className="flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground md:size-9"
          >
            <ArrowUpRight className="size-[18px]" strokeWidth={1.75} />
          </Link>
          {canManage && !project.tearingDown && <ProjectActionsMenu project={project} teams={teams} />}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-2 text-[13px] text-secondary md:mt-auto md:flex md:items-center md:gap-3 md:border-t md:border-[#242424] md:pt-4">
        <span className="flex min-w-0 items-center gap-2 whitespace-nowrap">
          <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", status === "Active" ? "bg-status-ok" : status === "Tearing down" ? "bg-status-warn" : "bg-muted-foreground")} />
          {status}
        </span>
        <span aria-hidden className="hidden h-3 w-px bg-border md:block" />
        <span className="flex min-w-0 items-center gap-1.5 whitespace-nowrap"><Layers className="size-3.5 shrink-0 md:hidden" strokeWidth={1.75} />{project.apps} {project.apps === 1 ? "app" : "apps"}</span>
        {project.teamName && <span aria-hidden className="hidden h-3 w-px bg-border md:block" />}
        <span className={cn("flex min-w-0 max-w-[40vw] items-center gap-1.5 md:max-w-none", !project.teamName && "md:hidden")}><Users className="size-3.5 shrink-0" strokeWidth={1.75} /><span className="truncate">{project.teamName ?? "No team"}</span></span>
        <span aria-hidden className="hidden h-3 w-px bg-border md:block" />
        <span className="flex min-w-0 items-center gap-1.5 md:truncate" suppressHydrationWarning><Clock className="size-3.5 shrink-0 md:hidden" strokeWidth={1.75} />{project.updatedAt ? `Updated ${relativeTime(project.updatedAt)}` : "No activity yet"}</span>
      </div>
    </article>
  );
}
