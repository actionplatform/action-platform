"use client";

import { KeyRound } from "lucide-react";
import Link from "next/link";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/copy-button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import type { Scope, ScopeInfo } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import { createApiToken } from "./actions";

export type TokenOrganization = { id: string; name: string; role: string; grantable: Scope[]; projects: { id: string; name: string; apps: { id: string; name: string }[] }[] };

const EVERY_ORG = "*";
const ALL = "";

export function NewTokenForm({ organizations, scopes, activeOrganizationId, server }: { organizations: TokenOrganization[]; scopes: ScopeInfo[]; activeOrganizationId: string; server: string }) {
  const [name, setName] = useState("");
  const [organizationId, setOrganizationId] = useState(activeOrganizationId);
  const [projectId, setProjectId] = useState(ALL);
  const [appId, setAppId] = useState(ALL);
  const [granted, setGranted] = useState<Scope[]>(["read"]);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<{ token: string; scope: string[]; expiresAt: number } | null>(null);
  const [pending, start] = useTransition();

  const everywhere = organizationId === EVERY_ORG;
  const organization = organizations.find((o) => o.id === organizationId);
  const grantable: Scope[] = everywhere ? [...new Set(organizations.flatMap((o) => o.grantable))] : (organization?.grantable ?? ["read"]);
  const projects = organization?.projects ?? [];
  const apps = projects.find((p) => p.id === projectId)?.apps ?? [];

  const pickOrganization = (id: string) => {
    setOrganizationId(id);
    setProjectId(ALL);
    setAppId(ALL);
    const allowed: Scope[] = id === EVERY_ORG ? [...new Set(organizations.flatMap((o) => o.grantable))] : (organizations.find((o) => o.id === id)?.grantable ?? ["read"]);
    setGranted((current) => current.filter((s) => allowed.includes(s)));
  };

  const toggle = (s: Scope) => {
    if (s === "read" || !grantable.includes(s)) return;
    setGranted((current) => (current.includes(s) ? current.filter((x) => x !== s) : [...current, s]));
  };

  const submit = () => start(async () => {
    setError(null);
    const r = await createApiToken({ name, scope: granted, organizationId, projectId: projectId || null, appId: appId || null });
    if (!r.ok) { setError(r.error); return; }
    setIssued(r.data);
  });

  if (issued) {
    return (
      <Panel>
        <PanelHeader title="Token created" description="Copy it now: it is shown only once. Revoke it under API tokens when it is no longer needed." />
        <PanelBody className="space-y-4">
          <div className="flex items-start gap-2 rounded-[8px] border border-border bg-background p-3">
            <code className="min-w-0 flex-1 break-all font-mono text-xs">{issued.token}</code>
            <CopyButton text={issued.token} label="Copy token" />
          </div>
          <div className="text-[13px] text-secondary">
            Scope <span className="text-foreground">{issued.scope.join(", ")}</span>, expires {new Date(issued.expiresAt).toLocaleDateString()}. Sign the CLI in without a browser by piping it in:
          </div>
          <pre className="overflow-x-auto rounded-[8px] border border-border bg-background p-3 font-mono text-xs">{`action-platform login ${server} --token < token.txt`}</pre>
          <div className="text-[13px] text-secondary">or set <code className="font-mono">AP_SERVER</code> and <code className="font-mono">AP_TOKEN</code> for the CLI and the MCP server.</div>
          <Link href="/organization/sessions" className="inline-flex h-9 items-center rounded-[7px] border border-border px-3 text-sm hover:bg-surface-hover">Back to API tokens</Link>
        </PanelBody>
      </Panel>
    );
  }

  return (
    <Panel>
      <PanelHeader title="New API token" description="A bearer token for automation, the CLI or an MCP server, for when no browser can approve a login. It acts as you, narrowed to the scope and reach chosen here." />
      <PanelBody className="space-y-5">
        <Field label="Name" hint="Shown in the API tokens list">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="ci-deploys" maxLength={80} disabled={pending} />
        </Field>

        <div>
          <div className="text-sm font-medium">Permissions</div>
          <ul className="mt-2 divide-y divide-border-subtle rounded-[8px] border border-border bg-background">
            {scopes.map((info) => {
              const s = info.id as Scope;
              const blocked = !grantable.includes(s);
              return (
                <li key={s} className={cn("flex items-start gap-3 px-3.5 py-3", blocked && "opacity-60")}>
                  <input type="checkbox" id={`token-scope-${s}`} className="mt-1 size-4 shrink-0 accent-foreground" checked={granted.includes(s)} disabled={blocked || s === "read" || pending} onChange={() => toggle(s)} />
                  <label htmlFor={`token-scope-${s}`} className="min-w-0 flex-1 cursor-pointer">
                    <div className="text-sm font-medium">{info.label}</div>
                    <div className="text-[13px] text-secondary">{blocked ? "Not available for your role here" : info.description}</div>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Organization">
            <Select value={organizationId} onChange={pickOrganization} options={[...(organizations.length > 1 ? [{ value: EVERY_ORG, label: "All organizations", hint: "role checked per organization" }] : []), ...organizations.map((o) => ({ value: o.id, label: o.name, hint: o.role }))]} disabled={pending} />
          </Field>
          {!everywhere && (
            <Field label="Project">
              <Select value={projectId} onChange={(v) => { setProjectId(v); setAppId(ALL); }} options={[{ value: ALL, label: "All projects" }, ...projects.map((p) => ({ value: p.id, label: p.name }))]} disabled={pending} />
            </Field>
          )}
          {!everywhere && projectId && (
            <Field label="App" className="sm:col-span-2">
              <Select value={appId} onChange={setAppId} options={[{ value: ALL, label: "All apps in the project" }, ...apps.map((a) => ({ value: a.id, label: a.name }))]} disabled={pending} />
            </Field>
          )}
        </div>

        <p className="text-[13px] text-secondary">Valid 90 days, or 30 days with Admin.</p>

        {error && <div className="rounded-[8px] border border-foreground px-3 py-2 text-sm" role="alert">{error}</div>}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Link href="/organization/sessions" className="inline-flex h-9 items-center justify-center rounded-[7px] border border-border px-3 text-sm hover:bg-surface-hover">Cancel</Link>
          <Button onClick={submit} disabled={pending || !name.trim()} loading={pending}><KeyRound className="size-4" strokeWidth={1.75} /> Create token</Button>
        </div>
      </PanelBody>
    </Panel>
  );
}
