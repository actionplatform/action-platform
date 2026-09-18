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
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
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
    <div className="space-y-3">
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      <DataTable
        title="Members"
        rows={members}
        rowKey={(m) => m.id}
        noun={["member", "members"]}
        minWidth={480}
        action={canManage ? <Button size="sm" variant="outline" disabled={candidates.length === 0} onClick={() => { setUserId(candidates[0]?.userId ?? ""); setAdding(true); }}><Plus className="size-3.5" strokeWidth={2} /> Add member</Button> : undefined}
        empty={{ icon: Users, title: "Nobody here yet", text: "Members must belong to the organization first." }}
        columns={[
          { key: "name", label: "Member", width: 45, render: (m) => <Inline><span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border text-[11px] font-semibold uppercase">{m.name.slice(0, 2)}</span><span className="truncate font-medium">{m.name}</span></Inline> },
          { key: "email", label: "Email", width: 45, hide: "sm", render: (m) => <Cell muted title={m.email}>{m.email}</Cell> },
          { key: "actions", label: "", width: 10, align: "right", render: (m) => canManage ? <button type="button" title="Remove from team" aria-label={`Remove ${m.name} from team`} disabled={pending} onClick={() => start(async () => { setError(null); const r = await removeMemberFromTeam(team.id, m.id); if (!r.ok) setError(r.error); })} className="inline-flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><UserMinus className="size-4" strokeWidth={1.75} /></button> : null },
        ]}
      />
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
    </div>
  );
}

function ProjectsPanel({ team, projects, candidates, canManage }: { team: { id: string }; projects: Project[]; candidates: CandidateProject[]; canManage: boolean }) {
  const [adding, setAdding] = useState(false);
  const [projectId, setProjectId] = useState(candidates[0]?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const chosen = candidates.find((c) => c.id === projectId);

  return (
    <div className="space-y-3">
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      <DataTable
        title="Projects"
        rows={projects}
        rowKey={(p) => p.id}
        noun={["project", "projects"]}
        minWidth={480}
        action={canManage ? <Button size="sm" variant="outline" disabled={candidates.length === 0} onClick={() => { setProjectId(candidates[0]?.id ?? ""); setAdding(true); }}><Plus className="size-3.5" strokeWidth={2} /> Assign project</Button> : undefined}
        empty={{ icon: FolderGit2, title: "No projects assigned", text: "A project belongs to one team at a time." }}
        columns={[
          { key: "name", label: "Project", width: 45, render: (p) => <Inline><FolderGit2 className="size-4 shrink-0 text-secondary" strokeWidth={1.75} /><Link href={`/projects/${p.id}`} className="truncate font-medium hover:underline underline-offset-4">{p.name}</Link></Inline> },
          { key: "slug", label: "Slug", width: 40, hide: "sm", render: (p) => <Cell mono muted>{p.slug}</Cell> },
          { key: "actions", label: "", width: 15, align: "right", render: (p) => <span className="inline-flex items-center gap-1"><Link href={`/projects/${p.id}`} title="Open project" aria-label={`Open ${p.name}`} className="inline-flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><ArrowUpRight className="size-4" strokeWidth={1.75} /></Link>{canManage && <button type="button" title="Unassign" aria-label={`Unassign ${p.name}`} disabled={pending} onClick={() => start(async () => { setError(null); const r = await setProjectTeam(team.id, p.id, false); if (!r.ok) setError(r.error); })} className="inline-flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><X className="size-4" strokeWidth={1.75} /></button>}</span> },
        ]}
      />
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
    </div>
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
