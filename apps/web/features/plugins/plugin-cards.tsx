"use client";

import { AlertCircle, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { savePluginOptions } from "./actions";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type PluginOption = { key: string; label: string; kind: string; help: string; required: boolean };
export type PluginCardData = { slug: string; name: string; version: string; description: string; error: string | null; options: PluginOption[]; values: Record<string, unknown> };

export function PluginCards({ plugins, canManage }: { plugins: PluginCardData[]; canManage: boolean }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {plugins.map((p) => <PluginCard key={p.slug} plugin={p} canManage={canManage} />)}
    </div>
  );
}

function configured(plugin: PluginCardData, values: Record<string, unknown>): boolean {
  return plugin.options.filter((o) => o.required && o.kind !== "bool").every((o) => String(values[o.key] ?? "").trim() !== "");
}

function initial(plugin: PluginCardData): Record<string, unknown> {
  return Object.fromEntries(plugin.options.map((o) => [o.key, plugin.values[o.key] ?? (o.kind === "bool" ? false : "")]));
}

function PluginCard({ plugin, canManage }: { plugin: PluginCardData; canManage: boolean }) {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, unknown>>(() => initial(plugin));
  const [saved, setSaved] = useState<Record<string, unknown>>(() => initial(plugin));
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const hasOptions = plugin.options.length > 0 && plugin.error === null;
  const ok = plugin.error === null && configured(plugin, saved);
  const complete = configured(plugin, values);
  const dirty = plugin.options.some((o) => String(values[o.key] ?? "").trim() !== String(saved[o.key] ?? "").trim());
  const state = plugin.error !== null ? "Failed to load" : !hasOptions ? "Installed" : ok ? "Configured" : "Not configured";
  const tone = plugin.error !== null ? "bad" : !hasOptions || ok ? "good" : "none";

  const submit = () => {
    setError(null);
    start(async () => {
      const r = await savePluginOptions(plugin.slug, values);
      if (r.ok) { setSaved(values); router.refresh(); } else setError(r.error);
    });
  };

  return (
    <section aria-labelledby={`plugin-${plugin.slug}`} className="flex flex-col rounded-[8px] border border-border bg-[#111111] p-4 transition-colors hover:border-border-hover">
      <div className="flex items-center gap-2.5">
        <h3 id={`plugin-${plugin.slug}`} className="text-[18px] font-semibold leading-6">{plugin.name}</h3>
        <span className={cn("ml-auto inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 text-[12px] font-medium", tone === "good" ? "border-[#1f4d2b] bg-[#0f1f14] text-[#7fd08f]" : tone === "bad" ? "border-[#5a2a2a] bg-[#1a0f0f] text-[#e07070]" : "border-border text-secondary")}>
          {tone === "good" && <Check className="size-3" strokeWidth={2.5} aria-hidden="true" />}
          {tone === "bad" && <AlertCircle className="size-3" strokeWidth={2.5} aria-hidden="true" />}
          {state}
        </span>
      </div>
      <p className="mt-2 text-sm leading-5 text-secondary">{plugin.description || plugin.slug}</p>
      {plugin.error !== null && <p className="mt-2 text-[13px] text-[#e07070]">{plugin.error}</p>}

      {hasOptions && (
        <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); if (canManage && complete && dirty) submit(); }}>
          {plugin.options.map((o) =>
            o.kind === "bool" ? (
              <label key={o.key} className="flex items-start gap-2.5 text-sm">
                <input type="checkbox" checked={!!values[o.key]} disabled={!canManage} onChange={(e) => setValues({ ...values, [o.key]: e.target.checked })} className="mt-0.5" />
                <span>
                  <span className="block">{o.label}</span>
                  {o.help && <span className="block text-xs text-muted-foreground">{o.help}</span>}
                </span>
              </label>
            ) : (
              <Field key={o.key} label={o.required ? o.label : `${o.label} (optional)`} hint={o.help || undefined}>
                <Input
                  type={o.kind === "secret" ? "password" : o.kind === "url" ? "url" : "text"}
                  value={String(values[o.key] ?? "")}
                  disabled={!canManage}
                  onChange={(e) => setValues({ ...values, [o.key]: e.target.value })}
                  placeholder={o.kind === "url" ? "https://" : undefined}
                  autoComplete="off"
                />
              </Field>
            ),
          )}
          {error && <p role="alert" className="text-sm text-[#e07070]">{error}</p>}
          {canManage && (
            <Button type="submit" className="h-10 w-full" disabled={pending || !complete || !dirty}>{pending ? "Saving…" : "Save"}</Button>
          )}
        </form>
      )}

      <div className="mt-auto flex h-6 items-center pt-3 text-[13px] text-muted-foreground">{plugin.version ? `v${plugin.version}` : ""}</div>
    </section>
  );
}
