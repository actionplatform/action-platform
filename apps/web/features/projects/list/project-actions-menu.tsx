"use client";

import { ArrowUpRight, MoreHorizontal, Trash2, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Menu } from "@/components/ui/menu";
import { AssignTeamDialog, DeleteProjectDialog } from "./project-dialogs";
import type { ProjectItem, TeamOption } from "./project-card";

export function ProjectActionsMenu({ project, teams }: { project: ProjectItem; teams: TeamOption[] }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  const [assigning, setAssigning] = useState(false);

  return (
    <>
      <Menu
        label={`Actions for ${project.name}`}
        items={[
          { label: "Open project", icon: <ArrowUpRight className="size-4" strokeWidth={1.75} />, onSelect: () => router.push(`/projects/${project.id}`) },
          { label: "Assign to team", icon: <Users className="size-4" strokeWidth={1.75} />, onSelect: () => setAssigning(true) },
          "separator",
          { label: "Delete project", icon: <Trash2 className="size-4" strokeWidth={1.75} />, danger: true, onSelect: () => setConfirm(true) },
        ]}
        trigger={({ open, toggle, id }) => (
          <button
            type="button"
            title="More actions"
            aria-label={`More actions for ${project.name}`}
            aria-haspopup="menu"
            aria-expanded={open}
            aria-controls={id}
            onClick={toggle}
            className="flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground md:size-9"
          >
            <MoreHorizontal className="size-[18px]" strokeWidth={1.75} />
          </button>
        )}
      />
      <AssignTeamDialog key={project.teamId ?? ""} project={project} teams={teams} open={assigning} onClose={() => setAssigning(false)} />
      <DeleteProjectDialog project={project} open={confirm} onClose={() => setConfirm(false)} onDeleted={() => router.refresh()} />
    </>
  );
}
