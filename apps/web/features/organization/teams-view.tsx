"use client";

import { ArrowUpRight, FolderGit2, Plus, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { newTeam } from "./teams-actions";

export type TeamItem = { id: string; name: string; slug: string; description: string | null; members: number; projects: number };

export function NewTeamButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="lg" onClick={() => setOpen(true)}><Plus className="size-4" strokeWidth={2} /> New team</Button>
      <NewTeamDialog open={open} onClose={() => setOpen(false)} />
    </>
  );
}

export function TeamsView({ teams, canManage }: { teams: TeamItem[]; canManage: boolean }) {
  const [creating, setCreating] = useState(false);

  return (
    <>
      {teams.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border px-6 py-16 text-center">
          <div className="flex size-12 items-center justify-center rounded-lg border border-[#303030]"><Users className="size-[22px] text-secondary" strokeWidth={1.5} /></div>
          <h2 className="mt-4 text-[17px] font-semibold">No teams yet</h2>
          <p className="mt-1 max-w-sm text-sm text-secondary">Teams group organization members and own projects. Members are invited under Settings.</p>
          {canManage && <Button className="mt-5" onClick={() => setCreating(true)}><Plus className="size-4" strokeWidth={2} /> New team</Button>}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {teams.map((t) => (
            <Link key={t.id} href={`/organization/teams/${t.id}`} className="group flex min-h-[180px] flex-col rounded-lg border border-border bg-surface px-6 py-[22px] transition-[border-color,background-color,transform] duration-150 ease-out hover:-translate-y-px hover:border-border-hover hover:bg-[#131313] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
              <div className="flex items-start justify-between">
                <div className="flex size-12 items-center justify-center rounded-lg border border-[#303030]"><Users className="size-[22px] text-secondary" strokeWidth={1.5} /></div>
                <ArrowUpRight className="size-[18px] text-muted-foreground transition-colors group-hover:text-foreground" strokeWidth={1.75} />
              </div>
              <div className="mt-4 mb-5 min-w-0">
                <h2 className="truncate text-[17px] font-semibold leading-6">{t.name}</h2>
                <div className="truncate text-[13px] text-secondary">{t.description || `${t.slug} · no description`}</div>
              </div>
              <div className="mt-auto flex items-center gap-3 border-t border-[#242424] pt-4 text-[13px] text-secondary">
                <span className="flex items-center gap-1.5"><Users className="size-3.5" strokeWidth={1.75} />{t.members} {t.members === 1 ? "member" : "members"}</span>
                <span aria-hidden className="h-3 w-px bg-border" />
                <span className="flex items-center gap-1.5"><FolderGit2 className="size-3.5" strokeWidth={1.75} />{t.projects} {t.projects === 1 ? "project" : "projects"}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
      <NewTeamDialog open={creating} onClose={() => setCreating(false)} />
    </>
  );
}

function NewTeamDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Dialog
      open={open}
      onClose={() => !pending && onClose()}
      title="New team"
      description="Add members and assign projects from the team page."
      footer={<><Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button><Button disabled={pending || !name.trim()} onClick={() => start(async () => { setError(null); const r = await newTeam(name, description); if (r.ok) { onClose(); setName(""); setDescription(""); router.push(`/teams/${r.data.id}`); } else setError(r.error); })}>{pending ? "Creating…" : "Create team"}</Button></>}
    >
      <div className="space-y-3">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Platform" autoFocus /></Field>
        <Field label="Description"><Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" /></Field>
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}
