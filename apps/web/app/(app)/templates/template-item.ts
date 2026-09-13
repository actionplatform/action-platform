import type { Matrix } from "@/lib/api";
import { CATEGORIES, CLOUD_ICONS, stackMeta, templateBrand, typeMeta } from "@/lib/catalog";

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
  brand: ReturnType<typeof templateBrand>;
  cloud: (typeof CLOUD_ICONS)[string] | null;
  source: string;
};

const categoryOf = (type: string) => CATEGORIES.find((c) => c.types?.includes(type))?.id ?? "all";

export function itemsFrom(m: Matrix): TemplateItem[] {
  const projects = m.projects.map<TemplateItem>((p) => ({
    id: `${p.source}:${p.type}/${p.stack}/${p.template}`,
    name: p.template,
    description: p.description,
    categoryId: categoryOf(p.type),
    categoryLabel: typeMeta(p.type).label,
    type: p.type,
    stack: p.stack || null,
    language: p.stack ? stackMeta(p.stack).label : null,
    isDefault: p.default,
    href: `/projects/_/apps/new?type=${p.type}${p.stack ? `&stack=${p.stack}` : ""}&template=${p.template}${p.source !== "official" ? `&source=${p.source}` : ""}`,
    brand: templateBrand(p.template, p.stack),
    cloud: null,
    source: p.source,
  }));
  const clouds = m.clouds.map<TemplateItem>((c) => ({
    id: `${c.source}:cloud/${c.name}`,
    name: c.name,
    description: c.description,
    categoryId: "cloud",
    categoryLabel: "Cloud overlay",
    type: "cloud",
    stack: null,
    language: c.languages.length ? c.languages.map((l) => stackMeta(l).label).join(", ") : null,
    isDefault: false,
    href: null,
    brand: CLOUD_ICONS[c.name]?.brand ?? null,
    cloud: CLOUD_ICONS[c.name] ?? null,
    source: c.source,
  }));
  return [...projects, ...clouds];
}

export const LIST_TITLES: Record<string, string> = {
  all: "All templates",
  web: "Web templates",
  libraries: "Library templates",
  docs: "Documentation templates",
  plugins: "Plugin templates",
  cloud: "Cloud templates",
  empty: "Empty templates",
};
