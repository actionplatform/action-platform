"use client";

import { ArrowUpRight, Cloud, FolderGit2, MoreHorizontal, Trash2, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Menu } from "@/components/ui/menu";
import { assignTeam, removeProject } from "./actions";
import { DangerIcon, DeleteRepositoryOption } from "@/features/projects";
import { TypeToConfirm } from "@/components/ui/type-to-confirm";
import type { ProjectItem, TeamOption } from "./project-card";

export function ProjectActionsMenu({ project, teams }: { project: ProjectItem; teams: TeamOption[] }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  const [repositories, setRepositories] = useState(false);
  const [cloud, setCloud] = useState(false);
  const [typed, setTyped] = useState("");
  const confirmed = typed.trim() === project.name;
  const [assigning, setAssigning] = useState(false);
  const [teamId, setTeamId] = useState(project.teamId ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <>
      <Menu
        label={`Actions for ${project.name}`}
        items={[
          { label: "Open project", icon: <ArrowUpRight className="size-4" strokeWidth={1.75} />, onSelect: () => router.push(`/projects/${project.id}`) },
          { label: "Assign to team", icon: <Users className="size-4" strokeWidth={1.75} />, onSelect: () => { setTeamId(project.teamId ?? ""); setAssigning(true); } },
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
            className="flex size-9 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
          >
            <MoreHorizontal className="size-[18px]" strokeWidth={1.75} />
          </button>
        )}
      />
      <Dialog
        open={assigning}
        onClose={() => !pending && setAssigning(false)}
        title={`Assign ${project.name} to a team`}
        description="Teams group the projects their members look after. Manage teams under Teams."
        footer={<><Button variant="ghost" onClick={() => setAssigning(false)} disabled={pending}>Cancel</Button><Button disabled={pending} onClick={() => start(async () => { setError(null); const r = await assignTeam(project.id, teamId || null); if (r.ok) setAssigning(false); else setError(r.error); })}>{pending ? "Saving…" : "Save"}</Button></>}
      >
        <div className="space-y-3">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Team</span>
            <Select autoFocus value={teamId} onChange={setTeamId} options={[{ value: "", label: "No team" }, ...teams.map((t) => ({ value: t.id, label: t.name }))]} />
          </label>
          {teams.length === 0 && <p className="text-xs text-muted-foreground">No teams yet. Create one under Teams.</p>}
          {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        </div>
      </Dialog>
      <ConfirmDialog
        open={confirm}
        onClose={() => { if (!pending) { setConfirm(false); setRepositories(false); setCloud(false); setTyped(""); setError(null); } }}
        icon={<DangerIcon />}
        title={`Delete ${project.name}?`}
        description="Every app in it goes too. This action is permanent and cannot be undone."
        confirmLabel="Delete project"
        confirmIcon={<Trash2 className="size-4" strokeWidth={1.75} aria-hidden="true" />}
        danger
        pending={pending}
        disabled={!confirmed}
        className="rounded-[14px]"
        onConfirm={() => start(async () => { setError(null); const r = await removeProject(project.id, repositories, cloud); if (r.ok) { setConfirm(false); setRepositories(false); setCloud(false); setTyped(""); router.refresh(); } else setError(r.error); })}
      >
        <div className="space-y-3">
          <DeleteRepositoryOption id={`delete-repos-${project.id}`} checked={repositories} onChange={setRepositories} disabled={pending} label="Delete repositories on the code host" icon={<FolderGit2 className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />} />
          {project.apps > 0 && <DeleteRepositoryOption id={`delete-cloud-${project.id}`} checked={cloud} onChange={setCloud} disabled={pending} label="Delete stacks on the cloud" icon={<Cloud className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />} />}
          <TypeToConfirm id={`confirm-delete-${project.id}`} expected={project.name} value={typed} onChange={setTyped} disabled={pending} />
          {confirm && error && <div role="alert" className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        </div>
      </ConfirmDialog>
    </>
  );
}
