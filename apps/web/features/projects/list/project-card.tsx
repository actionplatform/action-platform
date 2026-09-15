"use client";

import { ArrowUpRight, FolderGit2, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { relativeTime } from "@/lib/time";
import { cn } from "@/lib/utils";
import { ProjectActionsMenu } from "./project-actions-menu";

export type ProjectItem = { id: string; name: string; slug: string; description: string | null; apps: number; teamId: string | null; teamName: string | null; updatedAt: string };
export type TeamOption = { id: string; name: string };

export function ProjectCard({ project, teams, canManage }: { project: ProjectItem; teams: TeamOption[]; canManage: boolean }) {
  const router = useRouter();
  const href = `/projects/${project.id}`;
  const status = project.apps > 0 ? "Active" : "Empty";

  return (
    <article
      tabIndex={0}
      role="link"
      aria-label={`Open ${project.name}`}
      onClick={() => router.push(href)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); router.push(href); } }}
      className="group flex h-[180px] cursor-pointer flex-col rounded-[9px] border border-border bg-surface px-6 py-[22px] transition-[border-color,background-color,transform] duration-150 ease-out hover:-translate-y-px hover:border-border-hover hover:bg-[#131313] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
    >
      <div className="flex items-start justify-between">
        <div className="flex size-12 items-center justify-center rounded-lg border border-[#303030]">
          <FolderGit2 className="size-[22px] text-secondary" strokeWidth={1.5} />
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
          <Link
            href={href}
            title="Open project"
            aria-label={`Open ${project.name}`}
            className="flex size-9 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
          >
            <ArrowUpRight className="size-[18px]" strokeWidth={1.75} />
          </Link>
          {canManage && <ProjectActionsMenu project={project} teams={teams} />}
        </div>
      </div>

      <div className="mt-4 min-w-0">
        <h2 className="truncate text-[17px] font-semibold leading-6">{project.name}</h2>
        <div className="truncate font-mono text-[13px] text-secondary">{project.slug}</div>
      </div>

      <div className="mt-auto flex items-center gap-3 border-t border-[#242424] pt-4 text-[13px] text-secondary">
        <span className="flex items-center gap-2">
          <span aria-hidden className={cn("size-1.5 rounded-full", status === "Active" ? "bg-foreground" : "bg-muted-foreground")} />
          {status}
        </span>
        <span aria-hidden className="h-3 w-px bg-border" />
        <span>{project.apps} {project.apps === 1 ? "app" : "apps"}</span>
        {project.teamName && (
          <>
            <span aria-hidden className="h-3 w-px bg-border" />
            <span className="flex min-w-0 items-center gap-1.5"><Users className="size-3.5 shrink-0" strokeWidth={1.75} /><span className="truncate">{project.teamName}</span></span>
          </>
        )}
        <span aria-hidden className="h-3 w-px bg-border" />
        <span className="truncate" suppressHydrationWarning>{project.updatedAt ? `Updated ${relativeTime(project.updatedAt)}` : "No activity yet"}</span>
      </div>
    </article>
  );
}
