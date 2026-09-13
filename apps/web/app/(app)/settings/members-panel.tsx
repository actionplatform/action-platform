"use client";

import { Check, Copy, Link2, Mail, Trash2, UserMinus, UserPlus } from "lucide-react";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Table, Td, Th } from "@/components/ui/table";
import { type Role, ROLE_INFO, ROLES } from "@/lib/permissions";
import { addMember, changeRole, inviteMember, kickMember, revokeInvitation } from "./actions";

type Member = { id: string; userId: string; name: string; email: string; role: string };
type Pending = { id: string; email: string; role: string | null; inviter: string; expiresAt: string };

const ROLE_OPTIONS = ROLES.map((r) => ({ value: r, label: ROLE_INFO[r].label, hint: ROLE_INFO[r].description }));

export function MembersPanel({ org, members, invitations, me, canManage, origin }: { org: { name: string; slug: string }; members: Member[]; invitations: Pending[]; me: string; canManage: boolean; origin: string }) {
  const [inviting, setInviting] = useState(false);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Member | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Panel>
      <PanelHeader title="Members" aside={<div className="flex items-center gap-2"><Badge className="font-mono">{org.slug}</Badge>{canManage && <><Button size="sm" variant="outline" onClick={() => setInviting(true)}><Link2 className="size-3.5" strokeWidth={2} /> Invite</Button><Button size="sm" onClick={() => setAdding(true)}><UserPlus className="size-3.5" strokeWidth={2} /> Add member</Button></>}</div>} />
      <Table>
        <thead><tr><Th>member</Th><Th>email</Th><Th>role</Th>{canManage && <Th className="w-12"> </Th>}</tr></thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id}>
              <Td>{m.name}{m.userId === me && <span className="ml-2 text-xs text-muted-foreground">you</span>}</Td>
              <Td className="text-secondary">{m.email}</Td>
              <Td>
                {canManage ? (
                  <Select size="sm" className="w-36" aria-label={`Role of ${m.name}`} value={m.role === "member" ? "developer" : m.role} disabled={pending} options={ROLE_OPTIONS} onChange={(v) => start(async () => { setError(null); const r = await changeRole(m.id, v as Role); if (!r.ok) setError(r.error); })} />
                ) : <Badge>{m.role}</Badge>}
              </Td>
              {canManage && <Td><button type="button" title="Remove member" aria-label={`Remove ${m.name}`} disabled={pending || m.userId === me} onClick={() => setRemoving(m)} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground disabled:opacity-40"><UserMinus className="size-4" strokeWidth={1.75} /></button></Td>}
            </tr>
          ))}
        </tbody>
      </Table>
      {invitations.length > 0 && (
        <PanelBody className="border-t border-border">
          <div className="mb-2 text-xs text-secondary">Pending invitations</div>
          <ul className="space-y-1">
            {invitations.map((i) => <InvitationRow key={i.id} invitation={i} origin={origin} canManage={canManage} onError={setError} />)}
          </ul>
        </PanelBody>
      )}
      {error && <PanelBody><div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div></PanelBody>}
      <InviteDialog open={inviting} onClose={() => setInviting(false)} origin={origin} org={org} />
      <AddMemberDialog open={adding} onClose={() => setAdding(false)} org={org} />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        title={`Remove ${removing?.name} from ${org.name}?`}
        description="They lose access to every project and are dropped from all teams. Their account stays."
        confirmLabel="Remove member"
        danger
        pending={pending}
        onConfirm={() => { const m = removing; if (m) start(async () => { setError(null); const r = await kickMember(m.id); setRemoving(null); if (!r.ok) setError(r.error); }); }}
      />
    </Panel>
  );
}

function inviteUrl(origin: string, id: string) {
  return `${origin}/invite/${id}`;
}

function CopyLink({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button size="sm" variant="outline" onClick={async () => { try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {} }}>
      {copied ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />} {copied ? "Copied" : "Copy link"}
    </Button>
  );
}

function InvitationRow({ invitation, origin, canManage, onError }: { invitation: Pending; origin: string; canManage: boolean; onError: (e: string | null) => void }) {
  const [pending, start] = useTransition();
  return (
    <li className="flex flex-wrap items-center gap-3 rounded-md px-2 py-2 hover:bg-surface-hover">
      <Mail className="size-4 text-secondary" strokeWidth={1.75} />
      <div className="min-w-0 flex-1"><div className="truncate text-sm">{invitation.email}</div><div className="text-xs text-secondary">{invitation.role ?? "member"} · invited by {invitation.inviter} · expires {new Date(invitation.expiresAt).toLocaleDateString()}</div></div>
      <CopyLink url={inviteUrl(origin, invitation.id)} />
      {canManage && <button type="button" title="Revoke invitation" aria-label={`Revoke invitation for ${invitation.email}`} disabled={pending} onClick={() => start(async () => { onError(null); const r = await revokeInvitation(invitation.id); if (!r.ok) onError(r.error); })} className="flex size-8 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground"><Trash2 className="size-4" strokeWidth={1.75} /></button>}
    </li>
  );
}

function InviteDialog({ open, onClose, origin, org }: { open: boolean; onClose: () => void; origin: string; org: { name: string } }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("developer");
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const close = () => { if (pending) return; onClose(); setLink(null); setEmail(""); setRole("developer"); setError(null); };

  return (
    <Dialog
      open={open}
      onClose={close}
      title={`Invite to ${org.name}`}
      description="No email is sent. Share the invitation link with the person; it lets them sign in or create an account and join."
      footer={link ? <Button onClick={close}>Done</Button> : <><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !email.trim()} onClick={() => start(async () => { setError(null); const r = await inviteMember(email, role); if (r.ok) setLink(inviteUrl(origin, r.data.id)); else setError(r.error); })}>{pending ? "Creating…" : "Create invitation"}</Button></>}
    >
      {link ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2"><Link2 className="size-4 shrink-0 text-secondary" strokeWidth={1.75} /><code className="min-w-0 flex-1 truncate font-mono text-xs">{link}</code></div>
          <CopyLink url={link} />
          <p className="text-xs text-muted-foreground">Valid for 7 days, only for {email.trim().toLowerCase()}.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="person@company.com" autoFocus /></Field>
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Role</span>
            <Select value={role} onChange={(v) => setRole(v as Role)} options={ROLE_OPTIONS} />
          </label>
          <p className="text-xs text-muted-foreground">{ROLE_INFO[role].description}</p>
          {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        </div>
      )}
    </Dialog>
  );
}

function AddMemberDialog({ open, onClose, org }: { open: boolean; onClose: () => void; org: { name: string } }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("developer");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const close = () => { if (pending) return; onClose(); setName(""); setEmail(""); setPassword(""); setRole("developer"); setError(null); };
  const canSubmit = email.trim() && (name.trim() && password.length >= 8 || !name.trim() && !password);

  return (
    <Dialog
      open={open}
      onClose={close}
      title={`Add member to ${org.name}`}
      description="Creates the account right away with a password you hand over. For someone who already has an account, only the email is needed."
      footer={<><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending || !canSubmit} onClick={() => start(async () => { setError(null); const r = await addMember({ name, email, password, role }); if (r.ok) close(); else setError(r.error); })}>{pending ? "Adding…" : "Add member"}</Button></>}
    >
      <div className="space-y-3">
        <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="person@company.com" autoFocus /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name" hint="new accounts only"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Password" hint="at least 8 characters"><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        </div>
        <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Role</span>
          <Select value={role} onChange={(v) => setRole(v as Role)} options={ROLE_OPTIONS} />
        </label>
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}
