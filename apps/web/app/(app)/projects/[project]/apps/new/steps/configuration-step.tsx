"use client";

import { ExternalLink } from "lucide-react";
import { Field, Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { CI_PROVIDERS, ownerOf } from "../model";
import { Chip, Option, Section } from "../parts";
import type { AppWizard } from "../use-app-wizard";

export function ConfigurationStep({ w }: { w: AppWizard }) {
  const { config, setConfig, host, hosts } = w;
  return (
    <Section title="Configure your project" description="Set the project details before generating the files.">
      <div className="grid gap-4 sm:grid-cols-2">
        {!w.projectId && (
          <Field label="Project" hint="Which project this app belongs to." className="sm:col-span-2">
            <Select value={w.project} onChange={w.setProject} placeholder="Select a project…" options={w.projects.map((p) => ({ value: p.id, label: p.name }))} />
          </Field>
        )}
        <Field label="Project name" hint="Human name; the slug is derived from it." className="sm:col-span-2">
          <Input value={config.name} onChange={(e) => setConfig({ ...config, name: e.target.value })} placeholder="Orders API" autoFocus />
        </Field>
        <Field label="Directory" hint="Workspace folder on the platform.">
          <Input className="font-mono" value={config.directory} onChange={(e) => w.setDirectory(e.target.value)} />
        </Field>
        <Field label="Package name" hint="Importable module or package id.">
          <Input className="font-mono" value={config.packageName} onChange={(e) => w.setPackageName(e.target.value)} />
        </Field>
        <Field label="Description">
          <Input value={config.description} onChange={(e) => setConfig({ ...config, description: e.target.value })} placeholder={w.leaf?.description ?? ""} />
        </Field>
        <Field label="Source host" hint={hosts.length ? "Where the repository will live." : "None configured — Settings → Source hosts."}>
          <Select value={w.hostId} onChange={w.setHostId} disabled={hosts.length === 0} placeholder="No source host" options={hosts.map((h) => ({ value: h.id, label: h.name }))} />
        </Field>
        <Field label={host?.kind === "gitlab" ? "Namespace" : host?.kind === "bitbucket" ? "Workspace" : "Organization"} hint={host?.owners.length ? (host.kind === "gitlab" ? "Your user or a group where you can create projects." : host.kind === "bitbucket" ? "A workspace where you can create repositories." : "Where the repository is created — an account or organization the GitHub App is installed on.") : "Account or organization that owns the repository."}>
          {host?.owners.length ? (
            <div className="space-y-1.5">
              <Select mono value={config.githubOwner || ownerOf(host) || host.owners[0].account} onChange={(v) => setConfig({ ...config, githubOwner: v })} options={[...host.owners.map((o) => ({ value: o.account, label: o.account, hint: o.why ?? undefined, disabled: !o.ok })), ...(host.defaultOwner && !host.owners.some((o) => o.account === host.defaultOwner) ? [{ value: host.defaultOwner, label: host.defaultOwner }] : [])]} />
              {host.installUrl && <a href={host.installUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-secondary hover:text-foreground">Another organization? Install the GitHub App on it <ExternalLink className="size-3" strokeWidth={1.75} /></a>}
            </div>
          ) : (
            <div className="space-y-1.5">
              <Input className="font-mono" value={config.githubOwner} onChange={(e) => setConfig({ ...config, githubOwner: e.target.value })} placeholder={host?.kind === "bitbucket" ? "workspace-slug" : (host?.defaultOwner ?? "my-org")} />
              {host?.problem && <p className="text-xs text-secondary">{host.problem}</p>}
            </div>
          )}
        </Field>
      </div>

      <div className="mt-6">
        <div className="text-sm font-medium mb-2">Options</div>
        <div className="space-y-2">
          {w.type !== "empty" && (
            <Option checked={config.ci} onChange={(v) => setConfig({ ...config, ci: v })} label="Include CI workflow" hint="Lint, tests, Conventional Commits and git-flow on every pull request.">
              {config.ci && (
                <div className="flex gap-1 mt-2">
                  {CI_PROVIDERS.map((p) => <Chip key={p} active={config.ciProvider === p} onClick={() => w.setCiProvider(p)}>{p}</Chip>)}
                </div>
              )}
            </Option>
          )}
          {w.clouds.length > 0 && (
            <Option checked={config.cloud !== null} onChange={(v) => setConfig({ ...config, cloud: v ? w.clouds[0].name : null })} label="Include a deploy target" hint="Overlays the cloud files on top of the template and sets [deploy] target.">
              {config.cloud !== null && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {w.clouds.map((c) => <Chip key={c.name} active={config.cloud === c.name} onClick={() => setConfig({ ...config, cloud: c.name })}>{c.name}</Chip>)}
                </div>
              )}
            </Option>
          )}
          <div className="rounded-md border border-border px-3 py-2 text-sm">
            <div className="font-medium">Repository</div>
            <div className="text-[13px] text-secondary">{host ? `Created on ${host.name} as ${config.githubOwner || host.defaultOwner || "the token's user"}/${config.directory || "<directory>"} and pushed right away: apps on the platform always live on a code host.` : "Connect a code host in Settings first: the app is created on it and pushed right away."}</div>
          </div>
        </div>
      </div>
    </Section>
  );
}
