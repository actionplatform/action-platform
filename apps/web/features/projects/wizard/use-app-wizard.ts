"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import type { Matrix } from "@/lib/api";
import { call } from "@/lib/call";
import { initCommand, type Leaf, stacksFor, templatesFor, typesIn } from "@/lib/catalog";
import { slugify } from "@/lib/utils";
import { createAppFromTemplate } from "./actions";
import { type Config, type HostOption, type Preset, type ProjectOption, ciFor, ownerOf } from "./model";
import type { StepIndex } from "./stepper";

export function useAppWizard({ matrix, preset, projectId, projects, hosts }: { matrix: Matrix; preset: Preset; projectId: string | null; projects: ProjectOption[]; hosts: HostOption[] }) {
  const router = useRouter();
  const [project, setProject] = useState<string>(projectId ?? (projects.length === 1 ? projects[0].id : ""));
  const [hostId, setHostIdRaw] = useState<string>(hosts[0]?.id ?? "");
  const host = hosts.find((h) => h.id === hostId) ?? null;
  const [ciTouched, setCiTouched] = useState(false);
  const [step, setStep] = useState<StepIndex>(preset ? 3 : 0);
  const [type, setType] = useState<string | null>(preset?.type ?? null);
  const [stack, setStack] = useState<string | null>(preset?.stack ?? null);
  const [template, setTemplate] = useState<string | null>(preset?.template ?? null);
  const [source, setSource] = useState<string>(preset?.source ?? "official");
  const [config, setConfig] = useState<Config>({ name: "", directory: "", packageName: "", description: "", githubOwner: "", ci: true, ciProvider: ciFor(hosts[0]?.kind), cloud: null });
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
    setConfig((c) => ({ ...c, directory: touched.directory ? c.directory : slugify(c.name), packageName: touched.packageName ? c.packageName : slugify(c.name).replace(/-/g, "_") }));
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
  const pickTemplate = (t: Leaf) => { setTemplate(t.template); setSource(t.source); };
  const setHostId = (v: string) => {
    setHostIdRaw(v);
    if (!ciTouched) setConfig((c) => ({ ...c, ciProvider: ciFor(hosts.find((h) => h.id === v)?.kind) }));
  };
  const setCiProvider = (p: string) => { setCiTouched(true); setConfig((c) => ({ ...c, ciProvider: p })); };
  const setDirectory = (v: string) => { setTouched((t) => ({ ...t, directory: true })); setConfig((c) => ({ ...c, directory: slugify(v) })); };
  const setPackageName = (v: string) => { setTouched((t) => ({ ...t, packageName: true })); setConfig((c) => ({ ...c, packageName: v })); };

  const canContinue =
    step === 0 ? !!type
    : step === 1 ? (!hasStack || !!stack)
    : step === 2 ? !!template
    : step === 3 ? config.name.trim().length > 0 && config.directory.length > 0 && !!project && !!host && (host.kind !== "bitbucket" || !!(config.githubOwner || ownerOf(host)))
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
  const cancel = () => router.push(projectId ? `/projects/${projectId}` : "/projects");

  const command = initCommand({ type: type ?? "", stack: hasStack ? stack : null, template: templates.length > 1 ? template : null, name: config.name, ci: config.ci && type !== "empty" ? config.ciProvider : null, cloud: config.cloud, push: true });

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
        git_init: true,
        push: true,
        private: false,
      }, source), (error) => ({ ok: false as const, error }), "The app may have been created anyway: check the project before trying again.");
      if (r.ok) router.push(r.href);
      else setError(r.error);
    });

  return {
    matrix, preset, projectId, projects, hosts,
    step, setStep, type, stack, template, source, config, setConfig, project, setProject, hostId, setHostId, host,
    types, stacks, templates, leaf, hasStack, clouds,
    pickType, pickStack, pickTemplate, setCiProvider, setDirectory, setPackageName,
    canContinue, next, back, cancel, submit, command, error, pending,
  };
}

export type AppWizard = ReturnType<typeof useAppWizard>;
