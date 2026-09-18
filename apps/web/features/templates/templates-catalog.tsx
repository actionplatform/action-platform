"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import type { Matrix } from "@/lib/api";
import { categoriesFor } from "@/lib/catalog";
import { TemplateCategoryTabs } from "./template-category-tabs";
import { type OverlayTarget, TemplateCard, TemplateListItem } from "./template-card";
import { itemsFrom, listTitle } from "./template-item";
import { TemplatesNoneState, TemplatesNoResults } from "./templates-empty-state";
import { type TemplateView, TemplatesToolbar } from "./templates-toolbar";

const VIEW_KEY = "ap.templates.view";

export function TemplatesCatalog({ matrix, targets, canCreate, sources }: { matrix: Matrix; targets: OverlayTarget[]; canCreate: boolean; sources?: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const items = useMemo(() => itemsFrom(matrix), [matrix]);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [category, setCategory] = useState(params.get("category") ?? "all");
  const [language, setLanguage] = useState(params.get("language") ?? "all");
  const [view, setView] = useState<TemplateView>((params.get("view") as TemplateView) || "grid");

  useEffect(() => {
    if (params.get("view")) return;
    try {
      const saved = localStorage.getItem(VIEW_KEY);
      if (saved === "grid" || saved === "list") setView(saved);
    } catch {}
  }, [params]);

  useEffect(() => {
    const q = new URLSearchParams();
    if (search.trim()) q.set("q", search.trim());
    if (category !== "all") q.set("category", category);
    if (language !== "all") q.set("language", language);
    if (view !== "grid") q.set("view", view);
    const next = q.toString();
    if (next !== params.toString()) router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false });
  }, [search, category, language, view, pathname, router, params]);

  const changeView = useCallback((v: TemplateView) => {
    setView(v);
    try { localStorage.setItem(VIEW_KEY, v); } catch {}
  }, []);

  const languages = useMemo(() => {
    const seen = new Map<string, string>();
    for (const it of items) if (it.stack && it.language) seen.set(it.stack, it.language);
    return [...seen].map(([id, label]) => ({ id, label }));
  }, [items]);

  const tabs = useMemo(() => categoriesFor(matrix).map((c) => ({ id: c.id, label: c.label, count: c.id === "all" ? items.length : items.filter((i) => i.categoryId === c.id).length })), [matrix, items]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((it) => {
      if (category !== "all" && it.categoryId !== category) return false;
      if (language !== "all" && it.stack !== language) return false;
      if (!q) return true;
      return [it.name, it.description, it.categoryLabel, it.language ?? "", it.type].some((s) => s.toLowerCase().includes(q));
    });
  }, [items, search, category, language]);

  const clear = () => { setSearch(""); setCategory("all"); setLanguage("all"); };

  return (
    <>
      <PageHeader
        title="Templates"
        badge={<Badge className="h-6 bg-surface px-2 text-xs font-medium md:h-[26px] md:px-2.5">{items.length}<span className="hidden md:inline">&nbsp;{items.length === 1 ? "template" : "templates"}</span></Badge>}
        description="Start faster with production-ready foundations for apps, libraries, documentation, plugins, and cloud services."
        shortDescription="Production-ready foundations for your next project."
      />

      {sources}

      {items.length === 0 ? (
        <TemplatesNoneState />
      ) : (
        <>
          <TemplatesToolbar search={search} onSearch={setSearch} language={language} languages={languages} onLanguage={setLanguage} view={view} onView={changeView} />
          <TemplateCategoryTabs tabs={tabs} active={category} onChange={setCategory} />

          <div className="mt-[22px] mb-3.5 flex items-center justify-between">
            <h2 className="text-sm font-semibold">{listTitle(matrix, category)}</h2>
            <p role="status" aria-live="polite" className="text-[13px] text-secondary">{visible.length} {visible.length === 1 ? "result" : "results"}</p>
          </div>

          {visible.length === 0 ? (
            <TemplatesNoResults onClear={clear} />
          ) : view === "grid" ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((it) => <TemplateCard key={it.id} item={canCreate ? it : { ...it, href: null }} targets={targets} />)}
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border bg-surface">
              <div className="hidden h-10 items-center gap-4 border-b border-border px-4 text-xs font-medium text-muted-foreground md:flex">
                <span className="w-10" /><span className="flex-1">Template</span><span className="w-40">Category</span><span className="w-32">Language</span><span className="w-20" /><span className="w-[17px]" />
              </div>
              <div className="divide-y divide-border-subtle">
                {visible.map((it) => <TemplateListItem key={it.id} item={canCreate ? it : { ...it, href: null }} targets={targets} />)}
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
