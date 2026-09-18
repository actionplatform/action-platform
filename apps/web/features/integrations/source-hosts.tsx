"use client";

import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { Check, ChevronDown, ExternalLink, GitBranch, KeyRound, MoreHorizontal, Trash2, TriangleAlert, UserCog } from "lucide-react";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog, PromptDialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Menu } from "@/components/ui/menu";
import { RegistryCard } from "@/components/ui/registry-card";
import { Select } from "@/components/ui/select";
import type { HostAccess, Owner } from "@/lib/host-access";
import { HOST_KINDS, type HostKind, type SourceHost } from "@/lib/source-host-kinds";
import { cn } from "@/lib/utils";
import { changeHostOwner, createHost, deleteHost, rotateHostToken } from "./actions";

const BRANDS = { github: siGithub, gitlab: siGitlab, bitbucket: siBitbucket } as const;

type Props = { hosts: SourceHost[]; access?: Record<string, HostAccess>; canManage: boolean };

export function SourceHosts({ hosts, access = {}, canManage }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<HostKind>("github");
  const [state, action, pending] = useActionState(createHost, null);
  const meta = HOST_KINDS.find((k) => k.id === kind)!;

  useEffect(() => {
    if (state && state.error === undefined) {
      setOpen(false);
      router.refresh();
    }
  }, [state, router]);

  return (
    <RegistryCard
      title="Source hosts"
      description="Accounts this workspace pushes, releases and opens pull requests with."
      addLabel="Add with a token"
      canAdd={canManage}
      open={open}
      onToggle={() => setOpen((v) => !v)}
      count={hosts.length}
      empty={{ icon: GitBranch, title: "No source host yet", text: "Connect a provider above. Apps cannot be pushed, released or imported from a private repository until then." }}
      form={
        <form method="post" action={action} className="space-y-3">
          <input type="hidden" name="kind" value={kind} />
          <div className="flex gap-1 rounded-[8px] bg-surface-hover p-1 text-[13px]">
            {HOST_KINDS.map((k) => (
              <button key={k.id} type="button" onClick={() => setKind(k.id)} className={cn("flex-1 rounded-[6px] px-3 py-1.5 transition-colors", kind === k.id ? "bg-foreground font-medium text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{k.label}</button>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name"><Input name="name" placeholder={meta.label} /></Field>
            <Field label="Default owner" hint="Organization or user new repositories go under."><Input name="defaultOwner" className="font-mono" placeholder="org or user" /></Field>
            <Field label="Base URL" hint={meta.baseUrlHint} className="sm:col-span-2"><Input name="baseUrl" className="font-mono" /></Field>
            {meta.needsUsername && <Field label="Username"><Input name="username" required /></Field>}
            <Field label={meta.tokenLabel} hint={`${meta.tokenHint} Stored encrypted; never shown again.`} className={meta.needsUsername ? "" : "sm:col-span-2"}><Input name="token" type="password" className="font-mono" required /></Field>
          </div>
          {state?.error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{state.error}</div>}
          <div className="flex justify-end"><Button type="submit" size="sm" disabled={pending}>{pending ? "Saving…" : "Save host"}</Button></div>
        </form>
      }
    >
      {hosts.map((h) => <HostRow key={h.id} host={h} access={access[h.id]} canManage={canManage} />)}
    </RegistryCard>
  );
}

function accounts(a: HostAccess | undefined): { account: string; ok: boolean }[] {
  if (!a || !a.ok) return [];
  const seen = new Set<string>();
  return a.installations.filter((i) => (seen.has(i.account) ? false : seen.add(i.account))).map((i) => ({ account: i.account, ok: i.canCreateRepos && i.repositories === "all" }));
}

function HostRow({ host, access, canManage }: { host: SourceHost; access?: HostAccess; canManage: boolean }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [owner, setOwner] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const meta = HOST_KINDS.find((k) => k.id === host.kind);
  const brand = host.kind in BRANDS ? BRANDS[host.kind as keyof typeof BRANDS] : null;
  const chips = accounts(access);
  const shown = chips.slice(0, 2);
  const rest = chips.length - shown.length;
  const problems = access?.ok ? access.problems : access ? [access.error] : [];

  const menu = canManage ? (
    <Menu
      label={`Actions for ${host.name}`}
      items={[
        ...(chips.length ? [{ label: "Change default owner", icon: <UserCog className="size-4" strokeWidth={1.75} />, onSelect: () => setOwner(true) }] : []),
        ...(host.authKind === "token" ? [{ label: "Update token", icon: <KeyRound className="size-4" strokeWidth={1.75} />, onSelect: () => { setError(null); setRotating(true); } }] : []),
        "separator" as const,
        { label: "Remove host", icon: <Trash2 className="size-4" strokeWidth={1.75} />, danger: true, onSelect: () => setRemoving(true) },
      ]}
      trigger={({ open, toggle, id }) => (
        <button type="button" aria-label="Open source host actions" aria-haspopup="menu" aria-expanded={open} aria-controls={id} onClick={toggle} className="flex size-11 shrink-0 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-surface-hover hover:text-foreground md:size-8">
          <MoreHorizontal className="size-4" strokeWidth={1.75} />
        </button>
      )}
    />
  ) : null;

  const status = (
    <>
      <Badge tone={host.authKind === "oauth" ? "ok" : "neutral"} className="h-5 gap-1 px-2 text-[11px]">{host.authKind === "oauth" ? <><Check className="size-3" strokeWidth={2.5} /> Connected</> : "Token"}</Badge>
      {problems.length > 0 && <Badge tone="inverse" className="h-5 px-2 text-[11px]">{problems.length} {problems.length === 1 ? "issue" : "issues"}</Badge>}
    </>
  );

  return (
    <li className="px-4 py-3">
      <div className="rounded-[10px] border border-border bg-background p-4 md:hidden">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-[8px] border border-border bg-surface">
            {brand ? <BrandIcon icon={brand} mono className="size-4" /> : <GitBranch className="size-4 text-secondary" strokeWidth={1.75} />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{meta?.label ?? host.kind} · {host.name}</div>
            <div className="truncate text-[13px] text-secondary">{host.login ? `Signed in as ${host.login}` : host.username ? `Token for ${host.username}` : "Personal access token"}</div>
          </div>
          {menu}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">{status}</div>
        <button type="button" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded} className="mt-3 flex h-11 w-full items-center justify-center gap-1.5 rounded-[8px] border border-border text-sm text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
          View permissions <ChevronDown className={cn("size-4 transition-transform duration-150", expanded && "rotate-180")} strokeWidth={1.75} />
        </button>
        {expanded && <HostDetails host={host} access={access} mobile />}
      </div>

      <div className="hidden grid-cols-1 items-center gap-4 md:grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1.2fr)_auto]">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] border border-border bg-background">
            {brand ? <BrandIcon icon={brand} mono className="size-4" /> : <GitBranch className="size-4 text-secondary" strokeWidth={1.75} />}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-medium">{host.name}</span>
              <Badge className="h-5 px-2 text-[11px]">{meta?.label ?? host.kind}</Badge>
            </div>
            <div className="truncate text-[13px] text-secondary">{host.login ? `Signed in as ${host.login}` : host.username ? `Token for ${host.username}` : "Personal access token"}</div>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-2">{status}</div>
          <div className="mt-1 truncate text-[13px] text-secondary">{host.defaultOwner ? <>Owned by <span className="font-mono text-foreground">{host.defaultOwner}</span></> : "No default owner"}</div>
        </div>

        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{access?.ok && access.kind === "gitlab" ? "Namespaces" : access?.ok && access.kind === "bitbucket" ? "Workspaces" : "Installation accounts"}</div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {chips.length === 0 && <span className="text-[13px] text-muted-foreground">—</span>}
            {shown.map((c) => <span key={c.account} className={cn("inline-flex h-6 items-center rounded-[6px] border px-2 font-mono text-[12px]", c.ok ? "border-border bg-background" : "border-border text-muted-foreground line-through")}>{c.account}</span>)}
            {rest > 0 && <button type="button" onClick={() => setExpanded(true)} className="inline-flex h-6 items-center rounded-[6px] border border-border px-2 text-[12px] text-secondary hover:text-foreground">+{rest}</button>}
          </div>
        </div>

        <div className="flex items-center gap-1 lg:justify-end">
          <button type="button" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded} className="inline-flex h-8 items-center gap-1 rounded-[7px] px-2.5 text-[13px] text-secondary transition-colors hover:bg-surface-hover hover:text-foreground">
            View permissions <ChevronDown className={cn("size-3.5 transition-transform duration-150", expanded && "rotate-180")} strokeWidth={1.75} />
          </button>
          {menu}
        </div>
      </div>

      {expanded && <div className="hidden md:block"><HostDetails host={host} access={access} /></div>}
      {error && <div className="mt-3 rounded-md border border-foreground px-3 py-2 text-[13px]">{error}</div>}

      <ConfirmDialog
        open={removing}
        onClose={() => setRemoving(false)}
        title={`Remove ${host.name}?`}
        description="Apps that use it lose their credentials until another host is picked."
        confirmLabel="Remove host"
        danger
        pending={pending}
        onConfirm={() => start(async () => { await deleteHost(host.id); setRemoving(false); router.refresh(); })}
      />
      <PromptDialog
        open={rotating}
        onClose={() => setRotating(false)}
        title={`Update token for ${host.name}`}
        description={meta?.tokenHint}
        label={meta?.tokenLabel ?? "Token"}
        hint="Replaces the stored token; the old one is discarded."
        type="password"
        submitLabel="Update token"
        pending={pending}
        error={error}
        onSubmit={(value) => start(async () => { const r = await rotateHostToken(host.id, value); if (r?.error) setError(r.error); else { setRotating(false); router.refresh(); } })}
      />
      <Dialog
        open={owner}
        onClose={() => !pending && setOwner(false)}
        title="Default owner"
        description="Pre-selected as the organization when creating an app from this host."
        footer={<Button variant="ghost" onClick={() => setOwner(false)}>Close</Button>}
      >
        <Select mono value={host.defaultOwner ?? ""} disabled={pending} options={chips.map((c) => ({ value: c.account, label: c.account, hint: c.ok ? undefined : "cannot create repositories" }))} onChange={(v) => start(async () => { const r = await changeHostOwner(host.id, v); if (!r.ok) setError(r.error); else { setOwner(false); router.refresh(); } })} />
      </Dialog>
    </li>
  );
}

function HostDetails({ host, access, mobile = false }: { host: SourceHost; access?: HostAccess; mobile?: boolean }) {
  return (
    <div className={cn("rounded-lg border border-border-subtle bg-background text-[13px]", mobile ? "mt-3 border-border bg-surface px-3 py-3" : "mt-4 px-4 py-3")}>
          {!access ? (
            <div className="text-secondary">Permissions are checked for GitHub, GitLab and Bitbucket hosts.</div>
          ) : !access.ok ? (
            <div><span className="font-medium">Access check failed.</span> <span className="text-secondary">{access.error}</span></div>
          ) : (
            <div className="space-y-3">
              {mobile ? (
                <dl className="divide-y divide-border-subtle rounded-[8px] border border-border bg-background px-3">
                  <div className="flex items-center justify-between gap-3 py-2"><dt className="text-muted-foreground">Signed in as</dt><dd className="truncate font-mono text-foreground">{access.login}</dd></div>
                  <div className="flex items-center justify-between gap-3 py-2"><dt className="text-muted-foreground">Base URL</dt><dd className="truncate font-mono text-foreground">{host.baseUrl ?? "default"}</dd></div>
                </dl>
              ) : (
                <div className="grid gap-x-6 gap-y-1 sm:grid-cols-[auto_1fr]">
                  <span className="text-muted-foreground">Signed in as</span><span className="font-mono">{access.login}</span>
                  <span className="text-muted-foreground">Base URL</span><span className="font-mono">{host.baseUrl ?? "default"}</span>
                </div>
              )}
              {access.installations.length > 0 && mobile && (
                <div>
                  <div className="mt-4 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{access.kind === "gitlab" ? "Namespaces" : access.kind === "bitbucket" ? "Workspaces" : "Installation accounts"}</div>
                  <ul className="mt-2 space-y-2">
                    {access.installations.map((i) => <InstallationCard key={i.account} installation={i} />)}
                  </ul>
                </div>
              )}
              {access.installations.length > 0 && !mobile && (
                <div className="overflow-x-auto">
                  <table className="w-full text-[13px]">
                    <thead><tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground"><th className="py-1.5 pr-4 font-medium">Account</th><th className="py-1.5 pr-4 font-medium">Repositories</th><th className="py-1.5 pr-4 font-medium">Administration</th><th className="py-1.5 pr-4 font-medium">Contents</th><th className="py-1.5 font-medium">Can create</th></tr></thead>
                    <tbody className="divide-y divide-border-subtle">
                      {access.installations.map((i) => (
                        <tr key={i.account} className="align-top">
                          <td className="py-2 pr-4 font-mono">{i.account}</td>
                          <td className="py-2 pr-4">
                            {i.repositories === "all" ? "all" : (
                              <div>
                                <div className="flex items-center gap-2">
                                  <span>{i.selected?.length ?? 0} selected</span>
                                  {i.configureUrl && <a href={i.configureUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">Configure <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
                                </div>
                                {i.selected && i.selected.length > 0 && (
                                  <div className="mt-1.5 flex flex-wrap gap-1">
                                    {i.selected.map((r) => <span key={r} className="inline-flex h-5 items-center rounded-[5px] border border-border bg-surface px-1.5 font-mono text-[11px]">{r.split("/")[1] ?? r}</span>)}
                                  </div>
                                )}
                              </div>
                            )}
                          </td>
                          <td className="py-2 pr-4">{i.administration}</td>
                          <td className="py-2 pr-4">{i.contents}</td>
                          <td className="py-2">{i.canCreateRepos && i.repositories === "all" ? <Check className="size-4" strokeWidth={2.5} /> : <span className="text-muted-foreground">—</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {access.problems.length > 0 && mobile && (
                <ul className="space-y-2">
                  {access.problems.map((p) => (
                    <li key={p} className="flex gap-2.5 rounded-[8px] border border-border border-l-2 border-l-secondary bg-background px-3 py-2.5 text-[13px] text-secondary">
                      <TriangleAlert className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} />
                      <span className="min-w-0 [overflow-wrap:anywhere]">{p}</span>
                    </li>
                  ))}
                </ul>
              )}
              {access.problems.length > 0 && !mobile && <ul className="list-disc space-y-1 pl-5">{access.problems.map((p) => <li key={p}>{p}</li>)}</ul>}
              {access.installUrl && mobile && (
                <a href={access.installUrl} target="_blank" rel="noopener noreferrer" className="flex h-11 w-full items-center justify-center gap-1.5 rounded-[8px] border border-border bg-background text-sm text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">Install on another account <ExternalLink className="size-3.5" strokeWidth={1.75} /></a>
              )}
              {access.installUrl && !mobile && <a href={access.installUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-secondary hover:text-foreground">Install on another account <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
            </div>
          )}
    </div>
  );
}

function InstallationCard({ installation: i }: { installation: Owner }) {
  const canCreate = i.canCreateRepos && i.repositories === "all";
  return (
    <li className="min-w-0 rounded-[8px] border border-border bg-background p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-mono text-[13px]">{i.account}</span>
        <Badge className="h-5 shrink-0 px-2 text-[11px]">{i.repositories === "all" ? "all repositories" : `${i.selected?.length ?? 0} selected`}</Badge>
      </div>
      {i.repositories !== "all" && (
        <div className="mt-2 flex flex-wrap gap-1">
          {(i.selected ?? []).map((r) => <span key={r} className="inline-flex max-w-full items-center rounded-[5px] border border-border bg-surface px-1.5 py-0.5 font-mono text-[11px] [overflow-wrap:anywhere]">{r.split("/")[1] ?? r}</span>)}
          {i.configureUrl && <a href={i.configureUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 px-1 text-[11px] text-secondary hover:text-foreground">Configure <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
        </div>
      )}
      <dl className="mt-3 grid grid-cols-1 gap-2 min-[360px]:grid-cols-3">
        <div className="min-w-0"><dt className="text-[11px] text-muted-foreground">Administration</dt><dd className="truncate text-[13px] text-foreground">{i.administration}</dd></div>
        <div className="min-w-0"><dt className="text-[11px] text-muted-foreground">Contents</dt><dd className="truncate text-[13px] text-foreground">{i.contents}</dd></div>
        <div className="min-w-0"><dt className="text-[11px] text-muted-foreground">Can create</dt><dd className="text-[13px] text-foreground">{canCreate ? <Check className="size-4" strokeWidth={2.5} /> : <span className="text-muted-foreground">—</span>}</dd></div>
      </dl>
    </li>
  );
}
