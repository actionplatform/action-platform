import type { Matrix } from "@/lib/api";
import { categoriesFor, stackMeta, templateIcon, typeMeta } from "@/lib/catalog";

export type TemplateItem = {
  id: string;
  name: string;
  description: string;
  categoryId: string;
  categoryLabel: string;
  type: string;
  stack: string | null;
  language: string | null;
  isDefault: boolean;
  href: string | null;
  icon: string | null;
  stackIcon: string | null;
  source: string;
  plain: boolean;
  url: string | null;
};

export function itemsFrom(m: Matrix): TemplateItem[] {
  const projects = m.projects.map<TemplateItem>((p) => ({
    id: `${p.source}:${p.type}/${p.stack}/${p.template}`,
    name: p.template,
    description: p.description,
    categoryId: p.plain ? "repos" : p.type,
    categoryLabel: p.plain ? "Repository" : typeMeta(m, p.type).label,
    type: p.type,
    stack: p.stack || null,
    language: p.stack ? stackMeta(m, p.stack).label : null,
    isDefault: p.default,
    href: `/projects/_/apps/new?type=${p.type}${p.stack ? `&stack=${p.stack}` : ""}&template=${p.template}${p.source !== "official" ? `&source=${p.source}` : ""}`,
    icon: templateIcon(m, p),
    stackIcon: p.stack_icon ?? (p.stack ? stackMeta(m, p.stack).icon : null),
    source: p.source,
    plain: p.plain,
    url: p.url ?? null,
  }));
  const clouds = m.clouds.map<TemplateItem>((c) => ({
    id: `${c.source}:cloud/${c.name}`,
    name: c.name,
    description: c.description,
    categoryId: "cloud",
    categoryLabel: "Cloud overlay",
    type: "cloud",
    stack: null,
    language: c.languages.length ? c.languages.map((l) => stackMeta(m, l).label).join(", ") : null,
    isDefault: false,
    href: null,
    icon: c.icon ?? null,
    stackIcon: null,
    source: c.source,
    plain: false,
    url: c.url ?? null,
  }));
  return [...projects, ...clouds];
}

export function listTitle(m: Matrix, category: string): string {
  if (category === "all") return "All templates";
  if (category === "cloud") return "Cloud templates";
  if (category === "repos") return "Repositories added by your organization";
  return `${categoriesFor(m).find((c) => c.id === category)?.label ?? "Templates"} templates`;
}
