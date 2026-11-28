"use client";

import { Cloud, FolderGit2, Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { TypeToConfirm } from "@/components/ui/type-to-confirm";
import { DangerIcon, DeleteRepositoryOption } from "@/features/projects";
import { assignTeam, removeProject } from "./actions";

export type ProjectRef = { id: string; name: string; teamId: string | null; apps: number };
export type TeamChoice = { id: string; name: string };

export function AssignTeamDialog({ project, teams, open, onClose, onSaved }: { project: ProjectRef; teams: TeamChoice[]; open: boolean; onClose: () => void; onSaved?: () => void }) {
  const [teamId, setTeamId] = useState(project.teamId ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Dialog
      open={open}
      onClose={() => !pending && onClose()}
      title={`Assign ${project.name} to a team`}
      description="Teams group the projects their members look after. Manage teams under Teams."
      footer={<><Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button><Button disabled={pending} onClick={() => start(async () => { setError(null); const r = await assignTeam(project.id, teamId || null); if (r.ok) { onClose(); onSaved?.(); } else setError(r.error); })}>{pending ? "Saving…" : "Save"}</Button></>}
    >
      <div className="space-y-3">
        <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Team</span>
          <Select autoFocus value={teamId} onChange={setTeamId} options={[{ value: "", label: "No team" }, ...teams.map((t) => ({ value: t.id, label: t.name }))]} />
        </label>
        {teams.length === 0 && <p className="text-xs text-muted-foreground">No teams yet. Create one under Teams.</p>}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}

export function DeleteProjectDialog({ project, open, onClose, onDeleted }: { project: ProjectRef; open: boolean; onClose: () => void; onDeleted: () => void }) {
  const [repositories, setRepositories] = useState(false);
  const [cloud, setCloud] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const confirmed = typed.trim() === project.name;

  const reset = () => { setRepositories(false); setCloud(false); setTyped(""); setError(null); };

  return (
    <ConfirmDialog
      open={open}
      onClose={() => { if (!pending) { onClose(); reset(); } }}
      icon={<DangerIcon />}
      title={`Delete ${project.name}?`}
      description="Every app in it goes too. This action is permanent and cannot be undone."
      confirmLabel="Delete project"
      confirmIcon={<Trash2 className="size-4" strokeWidth={1.75} aria-hidden="true" />}
      danger
      pending={pending}
      disabled={!confirmed}
      className="rounded-[14px]"
      onConfirm={() => start(async () => { setError(null); const r = await removeProject(project.id, repositories, cloud); if (r.ok) { onClose(); reset(); onDeleted(); } else setError(r.error); })}
    >
      <div className="space-y-3">
        <DeleteRepositoryOption id={`delete-repos-${project.id}`} checked={repositories} onChange={setRepositories} disabled={pending} label="Delete repositories on the code host" icon={<FolderGit2 className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />} />
        {project.apps > 0 && <DeleteRepositoryOption id={`delete-cloud-${project.id}`} checked={cloud} onChange={setCloud} disabled={pending} label="Delete stacks on the cloud" icon={<Cloud className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />} />}
        <TypeToConfirm id={`confirm-delete-${project.id}`} expected={project.name} value={typed} onChange={setTyped} disabled={pending} />
        {open && error && <div role="alert" className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </ConfirmDialog>
  );
}
