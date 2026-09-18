"use client";

import { Check, MoreHorizontal, Server, Trash2, Wifi, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { RegistryCard } from "@/components/ui/registry-card";
import { CI_HOST_KINDS, CI_LABELS, type CiHost, type CiHostKind } from "@/lib/ci-kinds";
import { cn } from "@/lib/utils";
import { createCiHost, deleteCiHost, testCiHost } from "./actions";

type Props = { hosts: CiHost[]; canManage: boolean };

export function CiHosts({ hosts, canManage }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<CiHostKind>("jenkins");
  const [state, action, pending] = useActionState(createCiHost, null);
  const meta = CI_HOST_KINDS.find((k) => k.id === kind)!;

  useEffect(() => {
    if (state && state.error === undefined) {
      setOpen(false);
      router.refresh();
    }
  }, [state, router]);

  return (
    <RegistryCard
      title="CI servers"
      description="Build servers of their own, such as Jenkins. GitHub Actions needs nothing here: it reads with the source host\u2019s token."
      addLabel="Add a server"
      canAdd={canManage}
      open={open}
      onToggle={() => setOpen((v) => !v)}
      count={hosts.length}
      empty={{ icon: Server, title: "No CI server yet", text: "Add one above, then point an app at a job from its CI tab." }}
      form={
        <form method="post" action={action} className="space-y-3">
          <input type="hidden" name="kind" value={kind} />
          {CI_HOST_KINDS.length > 1 && (
            <div className="flex gap-1 rounded-[8px] bg-surface-hover p-1 text-[13px]">
              {CI_HOST_KINDS.map((k) => (
                <button key={k.id} type="button" onClick={() => setKind(k.id)} className={cn("flex-1 rounded-[6px] px-3 py-1.5 transition-colors", kind === k.id ? "bg-foreground font-medium text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{k.label}</button>
              ))}
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name"><Input name="name" placeholder={meta.label} /></Field>
            <Field label="Base URL" hint={meta.baseUrlHint}><Input name="baseUrl" className="font-mono" required /></Field>
            {meta.needsUsername && <Field label="Username"><Input name="username" required /></Field>}
            <Field label={meta.tokenLabel} hint={`${meta.tokenHint} Stored encrypted; never shown again.`} className={meta.needsUsername ? "" : "sm:col-span-2"}><Input name="token" type="password" className="font-mono" required /></Field>
          </div>
          {state?.error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{state.error}</div>}
          <div className="flex justify-end"><Button type="submit" size="sm" disabled={pending}>{pending ? "Saving…" : "Save server"}</Button></div>
        </form>
      }
    >
      {hosts.map((h) => <HostRow key={h.id} host={h} canManage={canManage} />)}
    </RegistryCard>
  );
}

function HostRow({ host, canManage }: { host: CiHost; canManage: boolean }) {
  const router = useRouter();
  const [removing, setRemoving] = useState(false);
  const [checked, setChecked] = useState<{ ok: boolean; error: string | null } | null>(null);
  const [pending, start] = useTransition();

  const test = () =>
    start(async () => {
      const r = await testCiHost(host.id);
      setChecked(r.ok ? r.data : { ok: false, error: r.error });
    });

  const remove = () =>
    start(async () => {
      await deleteCiHost(host.id);
      setRemoving(false);
      router.refresh();
    });

  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] border border-border"><Server className="size-4 text-secondary" strokeWidth={1.75} /></div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{host.name}</span>
          <Badge className="h-5 px-2 text-[11px]">{CI_LABELS[host.kind] ?? host.kind}</Badge>
          {checked && <Badge tone={checked.ok ? "success" : "danger"} className="h-5 gap-1 px-2 text-[11px]">{checked.ok ? <><Check className="size-3" strokeWidth={2.5} /> Reachable</> : <><X className="size-3" strokeWidth={2.5} /> {checked.error ?? "Unreachable"}</>}</Badge>}
        </div>
        <div className="mt-0.5 truncate font-mono text-xs text-secondary">{host.baseUrl}{host.username && <span className="text-muted-foreground"> · {host.username}</span>}</div>
      </div>
      <Button size="sm" variant="ghost" onClick={test} disabled={pending} aria-label={`Test ${host.name}`}><Wifi className="size-3.5" strokeWidth={2} /> <span className="hidden sm:inline">Test</span></Button>
      {canManage && (
        <Menu
          label={`Actions for ${host.name}`}
          items={[{ label: "Remove server", icon: <Trash2 className="size-4" strokeWidth={1.75} />, danger: true, onSelect: () => setRemoving(true) }]}
          trigger={({ open, toggle, id }) => (
            <button type="button" aria-label="Open CI server actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle} className="flex size-11 shrink-0 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-surface-hover hover:text-foreground md:size-8">
              <MoreHorizontal className="size-4" strokeWidth={1.75} />
            </button>
          )}
        />
      )}
      <ConfirmDialog open={removing} onClose={() => setRemoving(false)} onConfirm={remove} title={`Remove ${host.name}?`} description="Apps pointing at it lose their CI until they are connected again. Imported runs stay." confirmLabel="Remove" pending={pending} danger />
    </li>
  );
}
