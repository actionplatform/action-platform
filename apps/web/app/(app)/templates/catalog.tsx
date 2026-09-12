"use client";

import { ArrowUpRight, Cloud, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import type { Matrix } from "@/lib/api";
import { CATEGORIES, CLOUD_ICONS, stackMeta, templateBrand, typeMeta } from "@/lib/catalog";
import { cn } from "@/lib/utils";

export function Catalog({ matrix }: { matrix: Matrix }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [showFilters, setShowFilters] = useState(true);

  const cat = CATEGORIES.find((c) => c.id === category) ?? CATEGORIES[0];
  const q = query.trim().toLowerCase();
  const match = (...parts: (string | undefined)[]) => !q || parts.some((p) => p?.toLowerCase().includes(q));

  const projects = useMemo(
    () => matrix.projects.filter((p) => (cat.types ? cat.types.includes(p.type) : !cat.cloud) && match(p.template, p.description, p.stack, p.type)),
    [matrix, cat, q], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const clouds = useMemo(
    () => (cat.cloud || category === "all" ? matrix.clouds.filter((c) => match(c.name, c.description)) : []),
    [matrix, cat, category, q], // eslint-disable-line react-hooks/exhaustive-deps
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className={cn("flex flex-wrap gap-1.5", !showFilters && "hidden sm:flex")}>
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCategory(c.id)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                category === c.id ? "border-foreground bg-foreground text-primary-foreground" : "border-border bg-background text-foreground hover:border-border-hover",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2 sm:ml-auto">
          <label className="relative flex-1 sm:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search templates..." className="h-9 w-full pl-8 pr-3 text-sm" />
          </label>
          <Button variant="outline" size="md" className="sm:hidden" onClick={() => setShowFilters((v) => !v)}>
            <SlidersHorizontal className="size-4" /> Filters
          </Button>
        </div>
      </div>

      {(cat.types || category === "all") && (
        <section>
          {projects.length === 0 ? (
            <Empty />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p) => {
                const T = typeMeta(p.type);
                const brand = templateBrand(p.template, p.stack);
                const href = `/projects/_/apps/new?type=${p.type}${p.stack ? `&stack=${p.stack}` : ""}&template=${p.template}`;
                return (
                  <Link
                    key={`${p.type}/${p.stack}/${p.template}`}
                    href={href}
                    className="group flex flex-col rounded-lg border border-border bg-surface p-4 transition-colors hover:border-border-hover hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
                  >
                    <div className="flex items-start justify-between gap-3">
                      {brand ? <BrandIcon icon={brand} /> : <T.icon className="size-5 shrink-0" />}
                      <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <span className="font-mono font-medium">{p.template}</span>
                      {p.default && <Badge tone="inverse">Default</Badge>}
                    </div>
                    <p className="mt-1 text-sm text-secondary line-clamp-2">{p.description}</p>
                    <div className="mt-auto pt-3 flex gap-2 text-xs text-muted-foreground">
                      <span>{T.label}</span>
                      {p.stack && <><span>·</span><span>{stackMeta(p.stack).label}</span></>}
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </section>
      )}

      {clouds.length > 0 && (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold">Cloud overlays</h2>
            <p className="text-sm text-secondary">Pre-configured cloud deployment templates.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {clouds.map((c) => {
              const icon = CLOUD_ICONS[c.name];
              return (
                <div key={c.name} className="flex flex-col rounded-lg border border-border bg-surface p-4">
                  {icon?.brand ? <BrandIcon icon={icon.brand} /> : icon?.lucide ? <icon.lucide className="size-5" /> : <Cloud className="size-5" />}
                  <div className="mt-3 font-mono font-medium">{c.name}</div>
                  <p className="mt-1 text-sm text-secondary">{c.description}</p>
                  <div className="mt-auto pt-3 text-xs text-muted-foreground">
                    {c.types.length ? c.types.join(", ") : "any type"} · {c.languages.length ? c.languages.join(", ") : "any language"}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {cat.cloud && clouds.length === 0 && <Empty />}
    </div>
  );
}

function Empty() {
  return <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No templates match.</div>;
}
