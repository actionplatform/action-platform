"use client";

import { AlertTriangle, Check, KeyRound, Settings2, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { siSentry } from "simple-icons";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import type { ConnectionRow } from "@/lib/v1";
import { cn } from "@/lib/utils";
import { type AppMeta, OAuthAppDialog } from "./connect-hosts";
import { disconnectService } from "./oauth-actions";

type Kind = "sentry";

const META: Record<Kind, AppMeta & { icon: typeof siSentry; description: string }> = {
  sentry: {
    label: "Sentry",
    icon: siSentry,
    description: "Your authorization, kept by the platform and refreshed. Plugins that declare a Sentry connection read it instead of a pasted token.",
    callbackHint: "Sentry → User settings → API → Applications → Create New Application (Confidential)",
    baseUrlHint: "Self-hosted Sentry only, e.g. https://sentry.example.com",
  },
};

export function ConnectServices({ rows, origin, orgId, returnTo, canManage }: { rows: ConnectionRow[]; origin: string; orgId?: string; returnTo: string; canManage: boolean }) {
  const router = useRouter();
  const [setup, setSetup] = useState<Kind | null>(null);
  const [confirm, setConfirm] = useState<Kind | null>(null);
  const [pending, start] = useTransition();

  const startUrl = (kind: Kind) => {
    const q = new URLSearchParams({ return: returnTo });
    if (orgId) q.set("org", orgId);
    return `/api/oauth/${kind}/start?${q}`;
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {rows.filter((r) => r.kind in META).map((row) => {
        const kind = row.kind as Kind;
        const m = META[kind];
        return (
          <section key={kind} aria-labelledby={`service-${kind}`} className="flex min-h-[240px] flex-col rounded-[8px] border border-border bg-[#111111] p-4">
            <div className="flex items-center gap-2.5">
              <BrandIcon icon={m.icon} className="size-5" mono />
              <h3 id={`service-${kind}`} className="text-[18px] font-semibold leading-6">{m.label}</h3>
              <span className={cn("ml-auto inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 text-[12px] font-medium", row.connected ? "border-[#1f4d2b] bg-[#0f2416] text-[#6fd38a]" : "border-border text-secondary")}>
                {row.connected && <Check className="size-3" strokeWidth={2.5} aria-hidden="true" />}
                {row.connected ? "Connected" : "Not connected"}
              </span>
            </div>
            <p className="mt-2 text-sm leading-5 text-secondary">{m.description}</p>
            {row.connected && row.login && (
              <div className="mt-3 flex h-9 items-center gap-2 rounded-[6px] border border-border bg-background px-2.5 text-sm">
                <UserRound className="size-4 shrink-0 text-secondary" strokeWidth={1.75} aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate">{row.login}</span>
              </div>
            )}
            {row.connected && row.missing.length > 0 && (
              <div className="mt-3 flex gap-2 text-[13px] text-secondary">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[#e0b070]" strokeWidth={1.75} aria-hidden="true" />
                <span>Missing scopes: <code className="font-mono">{row.missing.join(" ")}</code>. Reconnect to grant them.</span>
              </div>
            )}
            {canManage && (
              <div className="mt-auto flex flex-col gap-2 pt-4">
                {row.configured ? (
                  <a href={startUrl(kind)} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
                    <KeyRound className="size-4" strokeWidth={1.75} aria-hidden="true" />
                    {row.connected ? `Reconnect ${m.label}` : `Connect ${m.label}`}
                  </a>
                ) : (
                  <Button variant="outline" className="h-10 w-full" onClick={() => setSetup(kind)}><Settings2 className="size-4" strokeWidth={1.75} aria-hidden="true" /> Set up OAuth app</Button>
                )}
                <div className="flex h-6 items-center justify-between text-[13px] text-muted-foreground">
                  {row.configured ? <button type="button" onClick={() => setSetup(kind)} className="rounded-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">Change OAuth app</button> : <span />}
                  {row.connected && <button type="button" onClick={() => setConfirm(kind)} className="rounded-sm hover:text-[#e07070] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">Disconnect</button>}
                </div>
              </div>
            )}
          </section>
        );
      })}
      {setup && <OAuthAppDialog provider={setup} meta={META[setup]} origin={origin} onClose={() => { setSetup(null); router.refresh(); }} onSaved={() => { setSetup(null); router.refresh(); }} />}
      <ConfirmDialog
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={`Disconnect ${confirm ? META[confirm].label : ""}?`}
        description="The stored token is deleted. Plugins that read this connection stop working until it is connected again or their token option is set. Revoke the authorization in the service too if you want it gone there."
        confirmLabel="Disconnect"
        danger
        pending={pending}
        onConfirm={() => { const k = confirm; if (k) start(async () => { const r = await disconnectService(k); if (r.ok) router.refresh(); setConfirm(null); }); }}
      />
    </div>
  );
}
