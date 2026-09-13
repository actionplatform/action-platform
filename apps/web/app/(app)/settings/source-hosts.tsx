"use client";

import { GitBranch, KeyRound, Plus, Trash2, X } from "lucide-react";
import { Fragment, useActionState, useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog, PromptDialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { HOST_KINDS, type HostKind, type SourceHost } from "@/lib/source-host-kinds";
import { cn } from "@/lib/utils";
import type { HostAccess } from "@/lib/host-access";
import { changeHostOwner, createHost, deleteHost, rotateHostToken } from "./actions";

export function SourceHosts({ hosts, access = {} }: { hosts: SourceHost[]; access?: Record<string, HostAccess> }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<HostKind>("github");
  const [state, action, pending] = useActionState(createHost, null);
  const [pendingRow, start] = useTransition();
  const [removing, setRemoving] = useState<SourceHost | null>(null);
  const [rotating, setRotating] = useState<SourceHost | null>(null);
  const [rotateError, setRotateError] = useState<string | null>(null);
  const meta = HOST_KINDS.find((k) => k.id === kind)!;

  useEffect(() => {
    if (state && state.error === undefined) setOpen(false);
  }, [state]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Source hosts</CardTitle>
        <Button size="sm" variant="ghost" onClick={() => setOpen((v) => !v)}>{open ? <X className="size-4" /> : <Plus className="size-4" />} {open ? "Close" : "Add with a token"}</Button>
      </CardHeader>

      {open && (
        <CardContent className="border-b border-border">
          <form action={action} className="space-y-3">
            <input type="hidden" name="kind" value={kind} />
            <div className="flex gap-1 rounded-md bg-surface-hover p-1 text-sm">
              {HOST_KINDS.map((k) => (
                <button key={k.id} type="button" onClick={() => setKind(k.id)} className={cn("flex-1 rounded px-3 py-1.5", kind === k.id ? "bg-foreground text-primary-foreground font-medium" : "text-muted-foreground hover:text-foreground")}>
                  {k.label}
                </button>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name"><Input name="name" placeholder={meta.label} /></Field>
              <Field label="Default owner" hint="Organization or user new repositories go under."><Input name="defaultOwner" className="font-mono" placeholder="org or user" /></Field>
              <Field label="Base URL" hint={meta.baseUrlHint} className="sm:col-span-2"><Input name="baseUrl" className="font-mono" /></Field>
              {meta.needsUsername && <Field label="Username"><Input name="username" required /></Field>}
              <Field label={meta.tokenLabel} hint={`${meta.tokenHint} Stored encrypted; never shown again.`} className={meta.needsUsername ? "" : "sm:col-span-2"}><Input name="token" type="password" className="font-mono" required /></Field>
            </div>
            {state?.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{state.error}</div>}
            <div className="flex justify-end"><Button type="submit" disabled={pending}>{pending ? "Saving…" : "Save host"}</Button></div>
          </form>
        </CardContent>
      )}

      <Table>
        <thead><tr><Th>name</Th><Th>kind</Th><Th>auth</Th><Th>base url</Th><Th>default owner</Th><Th /></tr></thead>
        <tbody>
          {hosts.length === 0 && <tr><Td colSpan={6} className="text-center text-muted-foreground py-6"><GitBranch className="inline size-4 mr-1" /> No source hosts yet. Apps cannot be pushed until one exists.</Td></tr>}
          {hosts.map((h) => (
            <Fragment key={h.id}>
            <tr>
              <Td className="font-medium">{h.name}</Td>
              <Td><Badge>{HOST_KINDS.find((k) => k.id === h.kind)?.label ?? h.kind}</Badge></Td>
              <Td><Badge tone={h.authKind === "oauth" ? "ok" : "neutral"}>{h.authKind === "oauth" ? "connected" : "token"}</Badge></Td>
              <Td className="font-mono text-xs text-secondary">{h.baseUrl ?? "—"}</Td>
              <Td className="font-mono text-xs">{ownerAccounts(access[h.id]).length > 0 ? <OwnerSelect host={h} accounts={ownerAccounts(access[h.id])} /> : (h.defaultOwner ?? "—")}</Td>
              <Td className="text-right whitespace-nowrap">
                {h.authKind === "token" && (
                  <Button variant="ghost" size="icon" title="Update token" onClick={() => { setRotateError(null); setRotating(h); }}>
                    <KeyRound className="size-4" />
                  </Button>
                )}
                <Button variant="ghost" size="icon" title="Remove" onClick={() => setRemoving(h)}>
                  <Trash2 className="size-4" />
                </Button>
              </Td>
            </tr>
            {access[h.id] && <AccessRow access={access[h.id]} />}
            </Fragment>
          ))}
        </tbody>
      </Table>

      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        title={`Remove ${removing?.name}?`}
        description="Apps that use it lose their credentials until another host is picked."
        confirmLabel="Remove host"
        danger
        pending={pendingRow}
        onConfirm={() => { const h = removing; if (h) start(async () => { await deleteHost(h.id); setRemoving(null); }); }}
      />
      <PromptDialog
        open={rotating !== null}
        onClose={() => setRotating(null)}
        title={`Update token for ${rotating?.name}`}
        description={rotating ? HOST_KINDS.find((k) => k.id === rotating.kind)?.tokenHint : undefined}
        label={rotating ? HOST_KINDS.find((k) => k.id === rotating.kind)!.tokenLabel : "Token"}
        hint="Replaces the stored token; the old one is discarded."
        type="password"
        submitLabel="Update token"
        pending={pendingRow}
        error={rotateError}
        onSubmit={(value) => { const h = rotating; if (h) start(async () => { const r = await rotateHostToken(h.id, value); if (r?.error) setRotateError(r.error); else setRotating(null); }); }}
      />
    </Card>
  );
}

function AccessRow({ access }: { access: HostAccess }) {
  if (!access.ok) return <tr><Td colSpan={6} className="border-t-0 pt-0 text-[13px]"><span className="text-foreground">Access check failed:</span> <span className="text-secondary">{access.error}</span></Td></tr>;
  return (
    <tr>
      <Td colSpan={6} className="border-t-0 pt-0">
        <div className="space-y-1.5 text-[13px]">
          <div className="flex flex-wrap items-center gap-2 text-secondary">
            <span>Signed in as <span className="font-mono text-foreground">{access.login}</span>.</span>
            {access.installations.length > 0 && <span>{access.kind === "github" ? "App installed on (each one can own new repositories):" : access.kind === "gitlab" ? "Namespaces that can own new projects:" : "Workspaces that can own new repositories:"}</span>}
            {access.installations.map((i) => (
              <Badge key={i.account} tone={i.canCreateRepos && i.repositories === "all" ? "ok" : "bad"} className="font-mono">{access.kind === "github" ? `${i.account} · ${i.repositories === "all" ? "all repos" : "selected repos"} · admin:${i.administration} · contents:${i.contents}` : i.account}</Badge>
            ))}
            {access.installUrl && <a href={access.installUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4 hover:text-foreground">Install on another account</a>}
          </div>
          {access.problems.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-foreground">{access.problems.map((p) => <li key={p}>{p}</li>)}</ul>
          ) : (
            <div className="text-secondary">Can create repositories and push.</div>
          )}
        </div>
      </Td>
    </tr>
  );
}

function OwnerSelect({ host, accounts }: { host: SourceHost; accounts: string[] }) {
  const [pending, start] = useTransition();
  const options = [...new Set([...(host.defaultOwner ? [host.defaultOwner] : []), ...accounts])].map((a) => ({ value: a, label: a }));
  return (
    <Select size="sm" mono className="w-44" aria-label={`Repository owner for ${host.name}`} value={host.defaultOwner ?? ""} disabled={pending} options={options} onChange={(v) => start(async () => { await changeHostOwner(host.id, v); })} />
  );
}

function ownerAccounts(a: HostAccess | undefined): string[] {
  if (!a || !a.ok) return [];
  return [...new Set([...a.installations.map((i) => i.account), a.login])];
}
