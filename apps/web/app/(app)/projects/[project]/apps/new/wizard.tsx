"use client";

import { ArrowRight, Check, Copy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandIcon } from "@/components/ui/brand-icon";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { Field, Input } from "@/components/ui/input";
import type { Matrix } from "@/lib/api";
import { countFor, initCommand, type Leaf, stackMeta, stacksFor, templateBrand, templatesFor, typeMeta, typesIn } from "@/lib/catalog";
import { cn, slugify } from "@/lib/utils";
import { createAppFromTemplate } from "./actions";
import { type StepIndex, Stepper } from "./stepper";

type Preset = { type: string; stack: string | null; template: string } | null;

type Config = {
  name: string;
  directory: string;
  packageName: string;
  description: string;
  githubOwner: string;
  gitInit: boolean;
  ci: boolean;
  ciProvider: string;
  docker: boolean;
  push: boolean;
};

const CI_PROVIDERS = ["github", "gitlab", "jenkins"];
const CONTINUE = ["Continue to stack", "Continue to template", "Continue to configuration", "Continue to review", "Create project"];

type ProjectOption = { id: string; name: string };
type HostOption = { id: string; name: string; kind: string; defaultOwner: string | null };

export function Wizard({ matrix, preset, projectId, projects, hosts }: { matrix: Matrix; preset: Preset; projectId: string | null; projects: ProjectOption[]; hosts: HostOption[] }) {
  const router = useRouter();
  const [project, setProject] = useState<string>(projectId ?? (projects.length === 1 ? projects[0].id : ""));
  const [hostId, setHostId] = useState<string>(hosts[0]?.id ?? "");
  const host = hosts.find((h) => h.id === hostId) ?? null;
  const [step, setStep] = useState<StepIndex>(preset ? 3 : 0);
  const [type, setType] = useState<string | null>(preset?.type ?? null);
  const [stack, setStack] = useState<string | null>(preset?.stack ?? null);
  const [template, setTemplate] = useState<string | null>(preset?.template ?? null);
  const [config, setConfig] = useState<Config>({
    name: "",
    directory: "",
    packageName: "",
    description: "",
    githubOwner: "",
    gitInit: true,
    ci: true,
    ciProvider: "github",
    docker: false,
    push: false,
  });
  const [touched, setTouched] = useState({ directory: false, packageName: false });
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const types = useMemo(() => typesIn(matrix), [matrix]);
  const stacks = useMemo(() => (type ? stacksFor(matrix, type) : []), [matrix, type]);
  const templates = useMemo(() => (type ? templatesFor(matrix, type, stack) : []), [matrix, type, stack]);
  const leaf: Leaf | undefined = templates.find((t) => t.template === template);
  const hasStack = stacks.length > 0;
  const dockerAllowed = useMemo(() => {
    const c = matrix.clouds.find((x) => x.name === "docker");
    if (!c || !leaf) return false;
    return (c.types.length === 0 || c.types.includes(leaf.type)) && (c.languages.length === 0 || c.languages.includes(leaf.stack));
  }, [matrix, leaf]);

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
  };
  const pickStack = (id: string) => {
    setStack(id);
    const tpls = templatesFor(matrix, type!, id);
    setTemplate(tpls.find((t) => t.default)?.template ?? (tpls.length === 1 ? tpls[0].template : null));
  };

  const canContinue =
    step === 0 ? !!type
    : step === 1 ? (!hasStack || !!stack)
    : step === 2 ? !!template
    : step === 3 ? config.name.trim().length > 0 && config.directory.length > 0 && !!project
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
    cloud: config.docker ? "docker" : null,
    push: config.push,
  });

  const submit = () =>
    start(async () => {
      setError(null);
      const r = await createAppFromTemplate(project, hostId || null, {
        type: type!,
        stack: hasStack ? stack : null,
        template,
        name: config.name.trim(),
        description: config.description,
        package_name: config.packageName || null,
        github_owner: config.githubOwner || null,
        ci: config.ci && type !== "empty" ? config.ciProvider : null,
        cloud: config.docker ? "docker" : null,
        git_init: config.gitInit,
        push: config.push,
        private: false,
      });
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
                  const m = stackMeta(id);
                  return (
                    <SelectCard key={id} selected={stack === id} onClick={() => pickStack(id)} compact>
                      {m.brand ? <BrandIcon icon={m.brand} /> : <span className="size-5 shrink-0 rounded-sm border border-border" />}
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
                  <SelectCard key={t.template} selected={template === t.template} onClick={() => setTemplate(t.template)}>
                    {(() => { const b = templateBrand(t.template, t.stack); return b ? <BrandIcon icon={b} className="mt-0.5" /> : null; })()}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-medium">{t.template}</span>
                        {t.default && <Badge tone="inverse">Default</Badge>}
                      </div>
                      <div className="text-sm text-secondary mt-1">{t.description}</div>
                      <div className="flex gap-2 mt-3 text-xs text-muted-foreground">
                        <span>{typeMeta(t.type).label}</span>
                        {t.stack && <><span>·</span><span>{stackMeta(t.stack).label}</span></>}
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
                    <select value={project} onChange={(e) => setProject(e.target.value)} className="h-9 w-full px-3 text-sm" required>
                      <option value="" disabled>Select a project…</option>
                      {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
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
                  <select value={hostId} onChange={(e) => setHostId(e.target.value)} className="h-9 w-full px-3 text-sm" disabled={hosts.length === 0}>
                    {hosts.length === 0 && <option value="">no source host</option>}
                    {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
                  </select>
                </Field>
                <Field label="Repository owner" hint="Organization or user; defaults to the host's.">
                  <Input className="font-mono" value={config.githubOwner} onChange={(e) => setConfig({ ...config, githubOwner: e.target.value })} placeholder={host?.defaultOwner ?? "my-org"} />
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
                            <Chip key={p} active={config.ciProvider === p} onClick={() => setConfig({ ...config, ciProvider: p })}>{p}</Chip>
                          ))}
                        </div>
                      )}
                    </Option>
                  )}
                  <Option checked={config.docker} disabled={!dockerAllowed} onChange={(v) => setConfig({ ...config, docker: v })} label="Include Docker configuration" hint={dockerAllowed ? "Dockerfile and compose overlay; deploy target set to docker." : "Not available for this template."} />
                  <Option checked disabled onChange={() => {}} label="Include code quality configuration" hint="Always on: .code_quality/ ships with every template." />
                  <Option checked={config.push} disabled={!host} onChange={(v) => setConfig({ ...config, push: v, gitInit: v || config.gitInit })} label="Create remote repository and push" hint={host ? `On ${host.name}, as ${config.githubOwner || host.defaultOwner || "the token's user"}/${config.directory || "<directory>"}.` : "Needs a source host."} />
                </div>
              </div>
            </Section>
          )}

          {step === 4 && (
            <Section title="Review your project" description="Confirm the configuration before creating the project.">
              <Card>
                <CardContent className="grid gap-x-8 gap-y-3 sm:grid-cols-2 text-sm">
                  <Row k="Type" v={type ? typeMeta(type).label : "—"} />
                  <Row k="Stack" v={stack ? stackMeta(stack).label : "—"} />
                  <Row k="Template" v={template ?? "—"} mono />
                  <Row k="Project name" v={config.name || "—"} />
                  <Row k="Directory" v={config.directory || "—"} mono />
                  <Row k="Package name" v={config.packageName || "—"} mono />
                  <Row k="Description" v={config.description || "—"} />
                  <Row k="Project" v={projects.find((p) => p.id === project)?.name ?? "—"} />
                  <Row k="Source host" v={host?.name ?? "—"} />
                  <Row k="Repository" v={host ? `${config.githubOwner || host.defaultOwner || "<token user>"}/${config.directory}` : "—"} mono />
                  <div className="sm:col-span-2">
                    <div className="text-xs text-secondary mb-1">Selected options</div>
                    <div className="flex flex-wrap gap-1">
                      {[
                        config.gitInit && "Git repository",
                        config.ci && type !== "empty" && `CI: ${config.ciProvider}`,
                        config.docker && "Docker",
                        "Code quality",
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
          type={type ? typeMeta(type).label : null}
          stack={stack ? stackMeta(stack).label : hasStack || !type ? null : "—"}
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
