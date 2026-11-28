"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { AssignTeamDialog, DeleteProjectDialog, type ProjectRef, type TeamChoice } from "./project-dialogs";

export function ProjectSettings({ project, teamName, teams }: { project: ProjectRef; teamName: string | null; teams: TeamChoice[] }) {
  const router = useRouter();
  const [assigning, setAssigning] = useState(false);
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader title="Team" />
        <PanelBody className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="text-secondary">{teamName ? <>This project belongs to <span className="text-foreground">{teamName}</span>.</> : "This project is not assigned to a team."}</p>
          <Button variant="outline" onClick={() => setAssigning(true)}>Assign to team</Button>
        </PanelBody>
      </Panel>
      <Panel>
        <PanelHeader title="Danger zone" />
        <PanelBody className="space-y-3 text-sm">
          <p className="text-secondary">Deleting removes this project and every app in it from the platform. This cannot be undone.</p>
          <Button variant="destructive" onClick={() => setConfirm(true)}>Delete project</Button>
        </PanelBody>
      </Panel>
      <AssignTeamDialog key={project.teamId ?? ""} project={project} teams={teams} open={assigning} onClose={() => setAssigning(false)} onSaved={() => router.refresh()} />
      <DeleteProjectDialog project={project} open={confirm} onClose={() => setConfirm(false)} onDeleted={() => router.push("/projects")} />
    </div>
  );
}
