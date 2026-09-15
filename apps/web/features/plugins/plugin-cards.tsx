"use client";

import { AlertCircle, Check, Settings2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { savePluginOptions } from "./actions";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type PluginOption = {
  key: string;
  label: string;
  kind: string;
  help: string;
  required: boolean;
};
export type PluginCardData = {
  slug: string;
  name: string;
  version: string;
  description: string;
  error: string | null;
  options: PluginOption[];
  values: Record<string, unknown>;
};

function configured(plugin: PluginCardData): boolean {
  return plugin.options
    .filter((o) => o.required)
    .every(
      (o) => plugin.values[o.key] !== undefined && plugin.values[o.key] !== "",
    );
}

export function PluginCards({
  plugins,
  canManage,
}: {
  plugins: PluginCardData[];
  canManage: boolean;
}) {
  const [editing, setEditing] = useState<PluginCardData | null>(null);
  const router = useRouter();

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plugins.map((p) => {
          const ok = p.error === null && configured(p);
          const state =
            p.error !== null
              ? "Failed to load"
              : p.options.length === 0
                ? "Installed"
                : ok
                  ? "Configured"
                  : "Not configured";
          return (
            <section
              key={p.slug}
              aria-labelledby={`plugin-${p.slug}`}
              className="flex min-h-[280px] flex-col rounded-[8px] border border-border bg-[#111111] p-4 transition-colors hover:border-border-hover"
            >
              <div className="flex items-center gap-2.5">
                <h3
                  id={`plugin-${p.slug}`}
                  className="text-[18px] font-semibold leading-6"
                >
                  {p.name}
                </h3>
                {p.description && <Hint text={p.description} />}
                <span
                  className={cn(
                    "ml-auto inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 text-[12px] font-medium",
                    ok || (p.error === null && p.options.length === 0)
                      ? "border-[#1f4d2b] bg-[#0f1f14] text-[#7fd08f]"
                      : p.error !== null
                        ? "border-[#5a2a2a] bg-[#1a0f0f] text-[#e07070]"
                        : "border-border text-secondary",
                  )}
                >
                  {(ok || (p.error === null && p.options.length === 0)) && (
                    <Check
                      className="size-3"
                      strokeWidth={2.5}
                      aria-hidden="true"
                    />
                  )}
                  {p.error !== null && (
                    <AlertCircle
                      className="size-3"
                      strokeWidth={2.5}
                      aria-hidden="true"
                    />
                  )}
                  {state}
                </span>
              </div>
              <p className="mt-2 font-mono text-[13px] text-secondary">{p.slug}</p>
              {p.error !== null && (
                <p className="mt-2 text-[13px] text-[#e07070]">{p.error}</p>
              )}

              {p.options.length > 0 && p.error === null && (
                <ul className="mt-3 space-y-1.5">
                  {p.options.map((o) => (
                    <li
                      key={o.key}
                      className="flex h-9 items-center gap-2 rounded-[6px] border border-border bg-background px-2.5 text-sm"
                    >
                      <span className="shrink-0 text-secondary">{o.label}</span>
                      <span className="min-w-0 flex-1 truncate text-right font-mono text-[13px]">
                        {display(o, p.values[o.key])}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-auto flex flex-col gap-2 pt-4">
                {p.options.length > 0 && p.error === null && canManage && (
                  <Button
                    variant={ok ? "outline" : "default"}
                    className="h-10 w-full"
                    onClick={() => setEditing(p)}
                  >
                    <Settings2
                      className="size-4"
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />{" "}
                    Configure
                  </Button>
                )}
                <div className="flex h-6 items-center text-[13px] text-muted-foreground">
                  {p.version ? `v${p.version}` : ""}
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {editing && (
        <PluginOptionsDialog
          plugin={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            router.refresh();
          }}
        />
      )}
    </>
  );
}

function display(option: PluginOption, value: unknown): string {
  if (value === undefined || value === "" || value === null) return "—";
  if (option.kind === "secret") return "••••••••";
  if (option.kind === "bool") return value ? "on" : "off";
  return String(value);
}

function PluginOptionsDialog({
  plugin,
  onClose,
  onSaved,
}: {
  plugin: PluginCardData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(
      plugin.options.map((o) => [
        o.key,
        plugin.values[o.key] ?? (o.kind === "bool" ? false : ""),
      ]),
    ),
  );
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const missing = plugin.options.filter(
    (o) =>
      o.required && o.kind !== "bool" && !String(values[o.key] ?? "").trim(),
  );

  const submit = () => {
    setError(null);
    start(async () => {
      const r = await savePluginOptions(plugin.slug, values);
      if (r.ok) onSaved();
      else setError(r.error);
    });
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={`Configure ${plugin.name}`}
      description={plugin.description || undefined}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={pending || missing.length > 0}>
            {pending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (missing.length === 0) submit();
        }}
      >
        {plugin.options.map((o) =>
          o.kind === "bool" ? (
            <label key={o.key} className="flex items-start gap-2.5 text-sm">
              <input
                type="checkbox"
                checked={!!values[o.key]}
                onChange={(e) =>
                  setValues({ ...values, [o.key]: e.target.checked })
                }
                className="mt-0.5"
              />
              <span>
                <span className="block">{o.label}</span>
                {o.help && (
                  <span className="block text-xs text-muted-foreground">
                    {o.help}
                  </span>
                )}
              </span>
            </label>
          ) : (
            <Field
              key={o.key}
              label={o.required ? o.label : `${o.label} (optional)`}
              hint={o.help || undefined}
            >
              <Input
                type={
                  o.kind === "secret"
                    ? "password"
                    : o.kind === "url"
                      ? "url"
                      : "text"
                }
                value={String(values[o.key] ?? "")}
                onChange={(e) =>
                  setValues({ ...values, [o.key]: e.target.value })
                }
                placeholder={o.kind === "url" ? "https://" : undefined}
                autoComplete="off"
              />
            </Field>
          ),
        )}
        {error && (
          <p role="alert" className="text-sm text-[#e07070]">
            {error}
          </p>
        )}
      </form>
    </Dialog>
  );
}
