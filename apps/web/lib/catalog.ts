// Presentation metadata for the templates matrix: labels, copy and line
// icons per project type and stack. The matrix itself comes from the API.
import { BookOpen, Cloud, FileBox, Globe, type LucideIcon, Package, Puzzle, Zap } from "lucide-react";
import {
  siApachemaven,
  siComposer,
  siDocker,
  siFastapi,
  siGin,
  siGo,
  siGooglechrome,
  siMaterialformkdocs,
  siNodedotjs,
  siNpm,
  siOpenjdk,
  siPhp,
  siPoetry,
  siPython,
  siReact,
  siRust,
  type SimpleIcon,
} from "simple-icons";
import type { Matrix } from "./api";

export type TypeMeta = { id: string; label: string; description: string; icon: LucideIcon };

export const TYPES: TypeMeta[] = [
  { id: "web", label: "Web application", description: "API, backend service, or frontend application.", icon: Globe },
  { id: "library", label: "Library", description: "Reusable package or language module.", icon: Package },
  { id: "docs", label: "Documentation", description: "Documentation site powered by MkDocs.", icon: BookOpen },
  { id: "plugin", label: "Browser plugin", description: "Chrome extension using Manifest V3.", icon: Puzzle },
  { id: "empty", label: "Empty project", description: "Minimal platform.toml foundation.", icon: FileBox },
];

// Brand shapes from Simple Icons, drawn in currentColor by <BrandIcon>.
export const STACKS: Record<string, { label: string; brand: SimpleIcon }> = {
  python: { label: "Python", brand: siPython },
  go: { label: "Go", brand: siGo },
  node: { label: "Node.js", brand: siNodedotjs },
  php: { label: "PHP", brand: siPhp },
  java: { label: "Java", brand: siOpenjdk },
  rust: { label: "Rust", brand: siRust },
  mkdocs: { label: "MkDocs", brand: siMaterialformkdocs },
  chrome: { label: "Chrome", brand: siGooglechrome },
};

// Per-template brand when the template is itself a known project (falls
// back to the stack's brand).
export const TEMPLATE_BRANDS: Record<string, SimpleIcon> = {
  fastapi: siFastapi,
  fastmcp: siPython,
  gin: siGin,
  react: siReact,
  poetry: siPoetry,
  module: siGo,
  composer: siComposer,
  npm: siNpm,
  maven: siApachemaven,
  cargo: siRust,
  material: siMaterialformkdocs,
  vanilla: siGooglechrome,
};

// AWS marks are not in Simple Icons (trademark policy); line icons instead.
export const CLOUD_ICONS: Record<string, { lucide?: LucideIcon; brand?: SimpleIcon }> = {
  "aws/lambda": { lucide: Zap },
  "aws/amplify": { lucide: Cloud },
  docker: { brand: siDocker },
};

export function typeMeta(id: string): TypeMeta {
  return TYPES.find((t) => t.id === id) ?? { id, label: id, description: "", icon: FileBox };
}

export function stackMeta(id: string): { label: string; brand: SimpleIcon | null } {
  return STACKS[id] ?? { label: id, brand: null };
}

export function templateBrand(template: string, stack: string): SimpleIcon | null {
  return TEMPLATE_BRANDS[template] ?? STACKS[stack]?.brand ?? null;
}

export type Leaf = Matrix["projects"][number];

export function typesIn(m: Matrix): TypeMeta[] {
  const present = new Set(m.projects.map((p) => p.type));
  return TYPES.filter((t) => present.has(t.id));
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

// Catalog filter chips → matrix types.
export const CATEGORIES: { id: string; label: string; types?: string[]; cloud?: boolean }[] = [
  { id: "all", label: "All" },
  { id: "web", label: "Web", types: ["web"] },
  { id: "libraries", label: "Libraries", types: ["library"] },
  { id: "docs", label: "Docs", types: ["docs"] },
  { id: "plugins", label: "Plugins", types: ["plugin"] },
  { id: "cloud", label: "Cloud", cloud: true },
  { id: "empty", label: "Empty", types: ["empty"] },
];

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
