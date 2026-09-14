"use client";

import { ArrowRight, Check, Copy, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandIcon } from "@/components/ui/brand-icon";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { Field, Input } from "@/components/ui/input";
import type { Matrix } from "@/lib/api";
import { countFor, initCommand, type Leaf, stackMeta, stacksFor, templateIcon, templatesFor, typeMeta, typesIn } from "@/lib/catalog";
import { cn, slugify } from "@/lib/utils";
import { call } from "@/lib/call";
import { createAppFromTemplate } from "./actions";
import { type StepIndex, Stepper } from "./stepper";

type Preset = { type: string; stack: string | null; template: string; source?: string } | null;

type Config = {
  name: string;
  directory: string;
  packageName: string;
  description: string;
  githubOwner: string;
  gitInit: boolean;
  ci: boolean;
  ciProvider: string;
  cloud: string | null;
  push: boolean;
};

function ownerOf(host: HostOption | null): string | null {
  if (!host) return null;
  if (host.owners.length === 0) return host.kind === "bitbucket" ? null : host.defaultOwner;
  return host.owners.some((o) => o.account === host.defaultOwner) ? host.defaultOwner : host.owners[0].account;
}

function ciFor(kind: string | undefined): string {
  return kind === "gitlab" ? "gitlab" : kind === "bitbucket" ? "bitbucket" : "github";
}

const CI_PROVIDERS = ["github", "gitlab", "jenkins", "bitbucket"];
const CONTINUE = ["Continue to stack", "Continue to template", "Continue to configuration", "Continue to review", "Create project"];

type ProjectOption = { id: string; name: string };
type OwnerOption = { account: string; ok: boolean; why: string | null };
type HostOption = { id: string; name: string; kind: string; defaultOwner: string | null; owners: readonly OwnerOption[]; installUrl: string | null; problem: string | null };

export function Wizard({ matrix, preset, projectId, projects, hosts }: { matrix: Matrix; preset: Preset; projectId: string | null; projects: ProjectOption[]; hosts: HostOption[] }) {
  const router = useRouter();
  const [project, setProject] = useState<string>(projectId ?? (projects.length === 1 ? projects[0].id : ""));
  const [hostId, setHostId] = useState<string>(hosts[0]?.id ?? "");
  const host = hosts.find((h) => h.id === hostId) ?? null;
  const [ciTouched, setCiTouched] = useState(false);
  const [step, setStep] = useState<StepIndex>(preset ? 3 : 0);
  const [type, setType] = useState<string | null>(preset?.type ?? null);
  const [stack, setStack] = useState<string | null>(preset?.stack ?? null);
  const [template, setTemplate] = useState<string | null>(preset?.template ?? null);
  const [source, setSource] = useState<string>(preset?.source ?? "official");
  const [config, setConfig] = useState<Config>({
    name: "",
    directory: "",
    packageName: "",
    description: "",
    githubOwner: "",
    gitInit: true,
    ci: true,
    ciProvider: ciFor(hosts[0]?.kind),
    cloud: null,
    push: false,
  });
  const [touched, setTouched] = useState({ directory: false, packageName: false });
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const types = useMemo(() => typesIn(matrix), [matrix]);
  const stacks = useMemo(() => (type ? stacksFor(matrix, type) : []), [matrix, type]);
  const templates = useMemo(() => (type ? [...templatesFor(matrix, type, stack), ...matrix.projects.filter((p) => p.plain && (p.type !== type || p.stack !== stack))] : []), [matrix, type, stack]);
  const leaf: Leaf | undefined = templates.find((t) => t.template === template && t.source === source);
  const hasStack = stacks.length > 0;
  const clouds = useMemo(() => {
    if (!leaf) return [];
    return matrix.clouds.filter((c) => c.source === leaf.source && (c.types.length === 0 || c.types.includes(leaf.type)) && (c.languages.length === 0 || c.languages.includes(leaf.stack)));
  }, [matrix, leaf]);

  useEffect(() => {
    setConfig((c) => (c.cloud && !clouds.some((x) => x.name === c.cloud) ? { ...c, cloud: null } : c));
  }, [clouds]);

  useEffect(() => {
    setConfig((c) => ({
      ...c,
      directory: touched.directory ? c.directory : slugify(c.name),
      packageName: touched.packageName ? c.packageName : slugify(c.name).replace(/-/g, "_"),
    }));
  }, [config.name, touched]);

  const pickType = (id: string) => {
    setType(id);
    setStack(null);
    const only = templatesFor(matrix, id, null);
    setTemplate(only.length === 1 ? only[0].template : null);
    setSource(only.length === 1 ? only[0].source : "official");
  };
  const pickStack = (id: string) => {
    setStack(id);
    const tpls = templatesFor(matrix, type!, id);
    const pick = tpls.find((t) => t.default) ?? (tpls.length === 1 ? tpls[0] : null);
    setTemplate(pick?.template ?? null);
    setSource(pick?.source ?? "official");
  };

  const canContinue =
    step === 0 ? !!type
    : step === 1 ? (!hasStack || !!stack)
    : step === 2 ? !!template
    : step === 3 ? config.name.trim().length > 0 && config.directory.length > 0 && !!project && (!config.push || !host || host.kind !== "bitbucket" || !!(config.githubOwner || ownerOf(host)))
    : true;

  const next = () => {
    if (step === 0 && !hasStack) return setStep(templates.length > 1 ? 2 : 3);
    if (step === 1 && templates.length === 1) return setStep(3);
    setStep((s) => Math.min(4, s + 1) as StepIndex);
  };
  const back = () => {
    if (step === 3 && preset) return router.push("/templates");
    if (step === 3 && !hasStack && templates.length <= 1) return setStep(0);
    if (step === 2 && !hasStack) return setStep(0);
    setStep((s) => Math.max(0, s - 1) as StepIndex);
  };

  const command = initCommand({
    type: type ?? "",
    stack: hasStack ? stack : null,
    template: templates.length > 1 ? template : null,
    name: config.name,
    ci: config.ci && type !== "empty" ? config.ciProvider : null,
    cloud: config.cloud,
    push: config.push,
  });

  const submit = () =>
    start(async () => {
      setError(null);
      const r = await call(() => createAppFromTemplate(project, hostId || null, {
        type: type!,
        stack: leaf?.plain ? leaf.stack || null : hasStack ? stack : null,
        template,
        name: config.name.trim(),
        description: config.description,
        package_name: config.packageName || null,
        github_owner: config.githubOwner || ownerOf(host),
        ci: config.ci && type !== "empty" ? config.ciProvider : null,
        cloud: config.cloud,
        git_init: config.gitInit,
        push: config.push,
        private: false,
      }, source), (error) => ({ ok: false as const, error }), "The app may have been created anyway: check the project before trying again.");
      if (r.ok) router.push(r.href);
      else setError(r.error);
    });

  return (
    <div className="space-y-6">
      <Stepper current={step} onJump={setStep} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 space-y-6">
          {step === 0 && (
            <Section title="What are you building?" description="Select a project type to get started.">
              <div className="grid gap-3 sm:grid-cols-2">
                {types.map((t) => (
                  <SelectCard key={t.id} selected={type === t.id} onClick={() => pickType(t.id)}>
                    <t.icon className="size-5 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium">{t.label}</div>
                      <div className="text-sm text-secondary mt-0.5">{t.description}</div>
                      <div className="text-xs text-muted-foreground mt-2">{plural(countFor(matrix, t.id), "template")}</div>
                    </div>
                  </SelectCard>
                ))}
              </div>
            </Section>
          )}

          {step === 1 && (
            <Section title="Choose your stack" description="Select the language or runtime for your project.">
              <div className="grid gap-3 sm:grid-cols-3">
                {stacks.map((id) => {
                  const m = stackMeta(matrix, id);
                  return (
                    <SelectCard key={id} selected={stack === id} onClick={() => pickStack(id)} compact>
                      {m.icon ? <BrandIcon src={m.icon} title={m.label} /> : <span className="size-5 shrink-0 rounded-sm border border-border" />}
                      <div className="min-w-0 flex-1">
                        <div className="font-medium">{m.label}</div>
                        <div className="text-xs text-muted-foreground">{plural(countFor(matrix, type!, id), "template")}</div>
                      </div>
                    </SelectCard>
                  );
                })}
              </div>
            </Section>
          )}

          {step === 2 && (
            <Section title="Choose a template" description="Select the foundation that best fits your project.">
              <div className="grid gap-3 sm:grid-cols-2">
                {templates.map((t) => (
                  <SelectCard key={`${t.source}:${t.template}`} selected={template === t.template && source === t.source} onClick={() => { setTemplate(t.template); setSource(t.source); }}>
                    {(() => { const b = templateIcon(matrix, t); return b ? <BrandIcon src={b} title={t.template} className="mt-0.5" /> : null; })()}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-medium">{t.template}</span>
                        {t.default && <Badge tone="inverse">Default</Badge>}
                        {t.source !== "official" && <Badge className="font-mono">{t.source}</Badge>}
                      </div>
                      <div className="text-sm text-secondary mt-1">{t.description}</div>
                      <div className="flex gap-2 mt-3 text-xs text-muted-foreground">
                        <span>{typeMeta(matrix, t.type).label}</span>
                        {t.stack && <><span>·</span><span>{stackMeta(matrix, t.stack).label}</span></>}
                      </div>
                    </div>
                  </SelectCard>
                ))}
              </div>
            </Section>
          )}

          {step === 3 && (
            <Section title="Configure your project" description="Set the project details before generating the files.">
              <div className="grid gap-4 sm:grid-cols-2">
                {!projectId && (
                  <Field label="Project" hint="Which project this app belongs to." className="sm:col-span-2">
                    <Select value={project} onChange={setProject} placeholder="Select a project…" options={projects.map((p) => ({ value: p.id, label: p.name }))} />
                  </Field>
                )}
                <Field label="Project name" hint="Human name; the slug is derived from it." className="sm:col-span-2">
                  <Input value={config.name} onChange={(e) => setConfig({ ...config, name: e.target.value })} placeholder="Orders API" autoFocus />
                </Field>
                <Field label="Directory" hint="Workspace folder on the platform.">
                  <Input className="font-mono" value={config.directory} onChange={(e) => { setTouched({ ...touched, directory: true }); setConfig({ ...config, directory: slugify(e.target.value) }); }} />
                </Field>
                <Field label="Package name" hint="Importable module or package id.">
                  <Input className="font-mono" value={config.packageName} onChange={(e) => { setTouched({ ...touched, packageName: true }); setConfig({ ...config, packageName: e.target.value }); }} />
                </Field>
                <Field label="Description">
                  <Input value={config.description} onChange={(e) => setConfig({ ...config, description: e.target.value })} placeholder={leaf?.description ?? ""} />
                </Field>
                <Field label="Source host" hint={hosts.length ? "Where the repository will live." : "None configured — Settings → Source hosts."}>
                  <Select value={hostId} onChange={(v) => { setHostId(v); if (!ciTouched) setConfig((c) => ({ ...c, ciProvider: ciFor(hosts.find((h) => h.id === v)?.kind) })); }} disabled={hosts.length === 0} placeholder="No source host" options={hosts.map((h) => ({ value: h.id, label: h.name }))} />
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
                  <Option checked={config.gitInit} onChange={(v) => setConfig({ ...config, gitInit: v })} label="Initialize Git repository" hint="First commit on main, git-flow hooks installed." />
                  {type !== "empty" && (
                    <Option checked={config.ci} onChange={(v) => setConfig({ ...config, ci: v })} label="Include CI workflow" hint="Lint, tests, Conventional Commits and git-flow on every pull request.">
                      {config.ci && (
                        <div className="flex gap-1 mt-2">
                          {CI_PROVIDERS.map((p) => (
                            <Chip key={p} active={config.ciProvider === p} onClick={() => { setCiTouched(true); setConfig({ ...config, ciProvider: p }); }}>{p}</Chip>
                          ))}
                        </div>
                      )}
                    </Option>
                  )}
                  {clouds.length > 0 && (
                    <Option checked={config.cloud !== null} onChange={(v) => setConfig({ ...config, cloud: v ? clouds[0].name : null })} label="Include a deploy target" hint="Overlays the cloud files on top of the template and sets [deploy] target.">
                      {config.cloud !== null && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {clouds.map((c) => (
                            <Chip key={c.name} active={config.cloud === c.name} onClick={() => setConfig({ ...config, cloud: c.name })}>{c.name}</Chip>
                          ))}
                        </div>
                      )}
                    </Option>
                  )}
                  <Option checked={config.push} disabled={!host} onChange={(v) => setConfig({ ...config, push: v, gitInit: v || config.gitInit })} label="Create remote repository and push" hint={host ? `On ${host.name}, as ${config.githubOwner || host.defaultOwner || "the token's user"}/${config.directory || "<directory>"}.` : "Needs a source host."} />
                </div>
              </div>
            </Section>
          )}

          {step === 4 && (
            <Section title="Review your project" description="Confirm the configuration before creating the project.">
              <Card>
                <CardContent className="grid gap-x-8 gap-y-3 sm:grid-cols-2 text-sm">
                  <Row k="Type" v={type ? typeMeta(matrix, type).label : "—"} />
                  <Row k="Stack" v={stack ? stackMeta(matrix, stack).label : "—"} />
                  <Row k="Template" v={template ?? "—"} mono />
                  <Row k="Project name" v={config.name || "—"} />
                  <Row k="Directory" v={config.directory || "—"} mono />
                  <Row k="Package name" v={config.packageName || "—"} mono />
                  <Row k="Description" v={config.description || "—"} />
                  <Row k="Project" v={projects.find((p) => p.id === project)?.name ?? "—"} />
                  <Row k="Source host" v={host?.name ?? "—"} />
                  <Row k="Repository" v={host ? `${config.githubOwner || ownerOf(host) || "<token user>"}/${config.directory}` : "—"} mono />
                  <div className="sm:col-span-2">
                    <div className="text-xs text-secondary mb-1">Selected options</div>
                    <div className="flex flex-wrap gap-1">
                      {[
                        config.gitInit && "Git repository",
                        config.ci && type !== "empty" && `CI: ${config.ciProvider}`,
                        config.cloud && `Deploy: ${config.cloud}`,
                        config.push && "Push to remote",
                      ].filter(Boolean).map((o) => <Badge key={String(o)} tone="ok">{o}</Badge>)}
                    </div>
                  </div>
                </CardContent>
              </Card>
              <CommandPreview command={command} />
              {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
            </Section>
          )}
        </div>

        <Summary
          type={type ? typeMeta(matrix, type).label : null}
          stack={stack ? stackMeta(matrix, stack).label : hasStack || !type ? null : "—"}
          template={template}
          configuration={config.name ? `${config.name} · ${config.directory}` : null}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button variant="ghost" onClick={() => router.push(projectId ? `/projects/${projectId}` : "/projects")}>Cancel</Button>
        <div className="flex gap-2 ml-auto">
          {(step > 0 || preset) && <Button variant="outline" onClick={back} disabled={pending}>Back</Button>}
          <Button onClick={step === 4 ? submit : next} disabled={!canContinue || pending}>
            {pending ? "Creating…" : CONTINUE[step]}
            {step < 4 ? <ArrowRight className="size-4" /> : <Check className="size-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-secondary">{description}</p>
      </div>
      {children}
    </section>
  );
}

function SelectCard({ selected, onClick, children, compact }: { selected: boolean; onClick: () => void; children: React.ReactNode; compact?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "flex items-start gap-3 rounded-lg border bg-surface text-left transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground",
        compact ? "p-3" : "p-4",
        selected ? "border-foreground" : "border-border hover:border-border-hover hover:bg-surface-hover",
      )}
    >
      {children}
      <CheckIndicator selected={selected} className="mt-0.5" />
    </button>
  );
}

function Option({ checked, disabled, onChange, label, hint, children }: { checked: boolean; disabled?: boolean; onChange: (v: boolean) => void; label: string; hint?: string; children?: React.ReactNode }) {
  return (
    <div className={cn("rounded-md border border-border p-3", disabled && "opacity-50")}>
      <label className="flex items-start gap-3 cursor-pointer">
        <button
          type="button"
          role="checkbox"
          aria-checked={checked}
          disabled={disabled}
          onClick={() => onChange(!checked)}
          className={cn("mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-sm border", checked ? "border-foreground bg-foreground text-primary-foreground" : "border-border-hover")}
        >
          {checked && <Check className="size-3" strokeWidth={3} />}
        </button>
        <span className="min-w-0 flex-1">
          <span className="block text-sm">{label}</span>
          {hint && <span className="block text-xs text-muted-foreground mt-0.5">{hint}</span>}
          {children}
        </span>
      </label>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("rounded-md border px-2.5 py-1 text-xs font-mono transition-colors", active ? "border-foreground bg-foreground text-primary-foreground" : "border-border text-foreground hover:border-border-hover")}
    >
      {children}
    </button>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-secondary mb-0.5">{k}</div>
      <div className={cn("break-words", mono && "font-mono text-xs")}>{v}</div>
    </div>
  );
}

function CommandPreview({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <div className="text-xs text-secondary mb-1">Equivalent command</div>
      <div className="relative rounded-md border border-border bg-background p-3 pr-10 font-mono text-xs overflow-x-auto">
        <code>{command}</code>
        <button
          type="button"
          title="Copy"
          onClick={() => { navigator.clipboard?.writeText(command); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
          className="absolute right-2 top-2 text-secondary hover:text-foreground"
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </button>
      </div>
    </div>
  );
}

function Summary({ type, stack, template, configuration }: { type: string | null; stack: string | null; template: string | null; configuration: string | null }) {
  return (
    <Card className="h-fit lg:sticky lg:top-8">
      <CardHeader><CardTitle>Your selection</CardTitle></CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Row k="Type" v={type ?? "—"} />
        <Row k="Stack" v={stack ?? "—"} />
        <Row k="Template" v={template ?? "—"} mono />
        <Row k="Configuration" v={configuration ?? "—"} />
        <Link href="/templates" className="block text-xs text-secondary underline underline-offset-4 hover:text-foreground">Browse the catalog</Link>
      </CardContent>
    </Card>
  );
}

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
