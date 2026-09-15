"use client";

import { ArrowUpRight, FolderGit2, Pencil, Plus, Trash2, UserMinus, Users, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { addMemberToTeam, editTeam, removeMemberFromTeam, removeTeam, setProjectTeam } from "./teams-actions";

type Member = { id: string; userId: string; name: string; email: string };
type Candidate = { userId: string; name: string; email: string };
type Project = { id: string; name: string; slug: string; description: string | null };
type CandidateProject = { id: string; name: string; teamName: string | null };

export function TeamDetail({ team, members, candidates, projects, candidatesProjects, canManage }: { team: { id: string; name: string; description: string }; members: Member[]; candidates: Candidate[]; projects: Project[]; candidatesProjects: CandidateProject[]; canManage: boolean }) {
  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <MembersPanel team={team} members={members} candidates={candidates} canManage={canManage} />
      <ProjectsPanel team={team} projects={projects} candidates={candidatesProjects} canManage={canManage} />
      {canManage && <SettingsPanel team={team} />}
    </div>
  );
}

function MembersPanel({ team, members, candidates, canManage }: { team: { id: string }; members: Member[]; candidates: Candidate[]; canManage: boolean }) {
  const [adding, setAdding] = useState(false);
  const [userId, setUserId] = useState(candidates[0]?.userId ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Panel>
      <PanelHeader title="Members" aside={canManage && <Button size="sm" variant="outline" disabled={candidates.length === 0} onClick={() => { setUserId(candidates[0]?.userId ?? ""); setAdding(true); }}><Plus className="size-3.5" strokeWidth={2} /> Add member</Button>} />
      <PanelBody className="space-y-1">
        {members.length === 0 && <p className="text-sm text-secondary">Nobody here yet. Members must belong to the organization first.</p>}
        {members.map((m) => (
          <div key={m.id} className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-surface-hover">
            <div className="flex size-8 items-center justify-center rounded-full border border-border text-xs font-semibold uppercase">{m.name.slice(0, 2)}</div>
            <div className="min-w-0 flex-1"><div className="truncate text-sm">{m.name}</div><div className="truncate text-xs text-secondary">{m.email}</div></div>
            {canManage && <button type="button" title="Remove from team" aria-label={`Remove ${m.name} from team`} disabled={pending} onClick={() => start(async () => { setError(null); const r = await removeMemberFromTeam(team.id, m.id); if (!r.ok) setError(r.error); })} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><UserMinus className="size-4" strokeWidth={1.75} /></button>}
          </div>
        ))}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </PanelBody>
      <Dialog
        open={adding}
        onClose={() => !pending && setAdding(false)}
        title="Add member"
        description="Only organization members can join a team. Invite people under Settings."
        footer={<><Button variant="ghost" onClick={() => setAdding(false)} disabled={pending}>Cancel</Button><Button disabled={pending || !userId} onClick={() => start(async () => { setError(null); const r = await addMemberToTeam(team.id, userId); if (r.ok) setAdding(false); else setError(r.error); })}>{pending ? "Adding…" : "Add"}</Button></>}
      >
        <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Member</span>
          <Select autoFocus value={userId} onChange={setUserId} options={candidates.map((c) => ({ value: c.userId, label: c.name, hint: c.email }))} />
        </label>
      </Dialog>
    </Panel>
  );
}

function ProjectsPanel({ team, projects, candidates, canManage }: { team: { id: string }; projects: Project[]; candidates: CandidateProject[]; canManage: boolean }) {
  const [adding, setAdding] = useState(false);
  const [projectId, setProjectId] = useState(candidates[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const chosen = candidates.find((c) => c.id === projectId);

  return (
    <Panel>
      <PanelHeader title="Projects" aside={canManage && <Button size="sm" variant="outline" disabled={candidates.length === 0} onClick={() => { setProjectId(candidates[0]?.id ?? ""); setAdding(true); }}><Plus className="size-3.5" strokeWidth={2} /> Assign project</Button>} />
      <PanelBody className="space-y-1">
        {projects.length === 0 && <p className="text-sm text-secondary">No projects assigned. A project belongs to one team at a time.</p>}
        {projects.map((p) => (
          <div key={p.id} className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-surface-hover">
            <div className="flex size-8 items-center justify-center rounded-md border border-border"><FolderGit2 className="size-4 text-secondary" strokeWidth={1.75} /></div>
            <div className="min-w-0 flex-1"><div className="truncate text-sm">{p.name}</div><div className="truncate font-mono text-xs text-secondary">{p.slug}</div></div>
            <Link href={`/projects/${p.id}`} title="Open project" aria-label={`Open ${p.name}`} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><ArrowUpRight className="size-4" strokeWidth={1.75} /></Link>
            {canManage && <button type="button" title="Unassign" aria-label={`Unassign ${p.name}`} disabled={pending} onClick={() => start(async () => { setError(null); const r = await setProjectTeam(team.id, p.id, false); if (!r.ok) setError(r.error); })} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><X className="size-4" strokeWidth={1.75} /></button>}
          </div>
        ))}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </PanelBody>
      <Dialog
        open={adding}
        onClose={() => !pending && setAdding(false)}
        title="Assign project"
        description="Moves the project under this team."
        footer={<><Button variant="ghost" onClick={() => setAdding(false)} disabled={pending}>Cancel</Button><Button disabled={pending || !projectId} onClick={() => start(async () => { setError(null); const r = await setProjectTeam(team.id, projectId, true); if (r.ok) setAdding(false); else setError(r.error); })}>{pending ? "Assigning…" : "Assign"}</Button></>}
      >
        <div className="space-y-2">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Project</span>
            <Select autoFocus value={projectId} onChange={setProjectId} options={candidates.map((c) => ({ value: c.id, label: c.name, hint: c.teamName ?? undefined }))} />
          </label>
          {chosen?.teamName && <p className="text-xs text-muted-foreground">Currently under {chosen.teamName}; it moves here.</p>}
        </div>
      </Dialog>
    </Panel>
  );
}

function SettingsPanel({ team }: { team: { id: string; name: string; description: string } }) {
  const router = useRouter();
  const [name, setName] = useState(team.name);
  const [description, setDescription] = useState(team.description);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const dirty = name !== team.name || description !== team.description;

  return (
    <Panel className="lg:col-span-2">
      <PanelHeader title="Team settings" aside={<Badge><Users className="size-3" strokeWidth={2} /> {team.name}</Badge>} />
      <PanelBody className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Description"><Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" /></Field>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={pending || !dirty || !name.trim()} onClick={() => start(async () => { setError(null); const r = await editTeam(team.id, name, description); if (!r.ok) setError(r.error); })}><Pencil className="size-3.5" strokeWidth={1.75} /> {pending ? "Saving…" : "Save"}</Button>
          <Button size="sm" variant="outline" disabled={pending} onClick={() => setConfirm(true)}><Trash2 className="size-3.5" strokeWidth={1.75} /> Delete team</Button>
        </div>
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </PanelBody>
      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        title={`Delete ${team.name}?`}
        description="Its projects stay in the organization without a team. Members keep their organization access."
        confirmLabel="Delete team"
        danger
        pending={pending}
        onConfirm={() => start(async () => { const r = await removeTeam(team.id); if (r.ok) router.push("/teams"); else { setConfirm(false); setError(r.error); } })}
      />
    </Panel>
  );
}
