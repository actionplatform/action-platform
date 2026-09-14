import { BookOpen, Bot, Cloud, Cog, FileBox, GitFork, Globe, type LucideIcon, Package, Puzzle } from "lucide-react";
import type { Matrix } from "./api";

export type Leaf = Matrix["projects"][number];
export type TypeMeta = { id: string; label: string; description: string; icon: LucideIcon };
export type StackMeta = { id: string; label: string; icon: string | null };

export const TYPE_ICONS: Record<string, LucideIcon> = {
  web: Globe,
  library: Package,
  automation: Cog,
  worker: Cog,
  bot: Bot,
  docs: BookOpen,
  plugin: Puzzle,
  cloud: Cloud,
  empty: FileBox,
  repos: GitFork,
};

export function typeIcon(id: string): LucideIcon {
  return TYPE_ICONS[id] ?? FileBox;
}

export function typeMeta(m: Matrix, id: string): TypeMeta {
  const found = m.types.find((t) => t.id === id);
  return { id, label: found?.label ?? id, description: found?.description ?? "", icon: typeIcon(id) };
}

export function stackMeta(m: Matrix, id: string): StackMeta {
  const found = m.stacks.find((s) => s.id === id);
  return { id, label: found?.label ?? id, icon: found?.icon ?? null };
}

export function templateIcon(m: Matrix, leaf: Leaf): string | null {
  return leaf.icon ?? leaf.stack_icon ?? (leaf.stack ? stackMeta(m, leaf.stack).icon : null);
}

export function typesIn(m: Matrix): TypeMeta[] {
  const present = [...new Set(m.projects.filter((p) => !p.plain).map((p) => p.type))];
  const ordered = m.types.map((t) => t.id).filter((id) => present.includes(id));
  const rest = present.filter((id) => !ordered.includes(id));
  return [...ordered, ...rest].map((id) => typeMeta(m, id));
}

export function stacksFor(m: Matrix, type: string): string[] {
  return [...new Set(m.projects.filter((p) => p.type === type && p.stack).map((p) => p.stack))];
}

export function templatesFor(m: Matrix, type: string, stack: string | null): Leaf[] {
  return m.projects.filter((p) => p.type === type && (stack === null || p.stack === stack));
}

export function countFor(m: Matrix, type: string, stack?: string): number {
  return m.projects.filter((p) => p.type === type && (stack === undefined || p.stack === stack)).length;
}

export type Category = { id: string; label: string; types?: string[]; cloud?: boolean; plain?: boolean };

export function categoriesFor(m: Matrix): Category[] {
  const types = typesIn(m).map<Category>((t) => ({ id: t.id, label: t.label, types: [t.id] }));
  return [{ id: "all", label: "All" }, ...types, { id: "cloud", label: "Cloud", cloud: true }, { id: "repos", label: "Repositories", plain: true }];
}

export function initCommand(input: {
  type: string;
  stack: string | null;
  template: string | null;
  name: string;
  ci: string | null;
  cloud: string | null;
  push: boolean;
}): string {
  const parts = ["action-platform init", input.type];
  if (input.stack) parts.push(input.stack);
  if (input.template) parts.push(input.template);
  if (input.name) parts.push(`--name "${input.name}"`);
  if (input.ci) parts.push(`--ci ${input.ci}`);
  if (input.cloud) parts.push(`--cloud ${input.cloud}`);
  if (!input.push) parts.push("--no-push");
  return parts.join(" ");
}
