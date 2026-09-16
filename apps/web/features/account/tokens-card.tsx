"use client";

import { Bot, KeyRound, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import type { UserToken } from "@/lib/api-tokens";
import type { ScopeInfo } from "@/lib/permissions";
import { relativeTime } from "@/lib/time";
import { revokeApiToken } from "./actions";

export function TokensCard({ tokens, now, scopes }: { tokens: UserToken[]; now: number; scopes: ScopeInfo[] }) {
  const label = (s: string) => scopes.find((x) => x.id === s)?.label ?? s;
  const router = useRouter();
  const [revoking, setRevoking] = useState<UserToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Card className="rounded-[11px]">
      <header className="border-b border-border px-4 py-4 md:px-6 md:py-5">
        <h2 className="text-[15px] font-semibold">API tokens<span className="hidden md:inline"> and the apps using them</span></h2>
        <p className="mt-1 text-[13px] text-secondary md:hidden">Tokens used by CLI and connected apps.</p>
        <p className="mt-1 hidden text-[13px] text-secondary md:block">Bearer tokens issued by <code className="font-mono">action-platform login</code>. Each token shows which programs have used it — Claude Code, Codex, Cursor, the CLI — and carries a scope on top of your role. Revoke what you no longer recognise.</p>
      </header>
      {tokens.length === 0 ? (
        <div className="flex flex-col items-center px-6 py-10 text-center">
          <div className="flex size-11 items-center justify-center rounded-[9px] border border-border"><KeyRound className="size-5 text-secondary" strokeWidth={1.5} /></div>
          <div className="mt-3 text-sm font-medium">No tokens yet</div>
          <div className="mt-1 max-w-sm text-[13px] text-secondary">Run <code className="font-mono">action-platform login &lt;server&gt; --scope read,write</code> and approve the code here.</div>
        </div>
      ) : (
        <ul className="divide-y divide-border-subtle">
          {tokens.map((t) => (
            <li key={t.id} className="flex flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:gap-4 md:px-6">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium">{t.name}</span>
                  {t.scope.map((s) => <Badge key={s} className="h-5 px-2 text-[11px]">{label(s)}</Badge>)}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-1 text-[12px] text-secondary">
                  <span className="inline-flex h-5 items-center rounded-[5px] border border-border bg-background px-1.5 font-mono text-[11px] text-foreground">{t.organization?.name ?? "all organizations"}</span>
                  {t.project && <><span aria-hidden>/</span><span className="inline-flex h-5 items-center rounded-[5px] border border-border bg-background px-1.5 font-mono text-[11px] text-foreground">{t.project.name}</span></>}
                  {t.app && <><span aria-hidden>/</span><span className="inline-flex h-5 items-center rounded-[5px] border border-border bg-background px-1.5 font-mono text-[11px] text-foreground">{t.app.name}</span></>}
                  {!t.project && <span>· every project</span>}
                </div>
                {t.clients.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    {t.clients.map((c) => <span key={c.name} className="inline-flex h-6 items-center gap-1.5 rounded-[6px] border border-border bg-background px-2 text-[12px]"><Bot className="size-3.5 text-secondary" strokeWidth={1.75} aria-hidden="true" />{c.product}{c.version && <span className="font-mono text-[11px] text-muted-foreground">{c.version}</span>}<span className="text-muted-foreground">· {relativeTime(c.lastSeenAt, now)}</span></span>)}
                  </div>
                )}
                <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[13px] text-secondary" suppressHydrationWarning>
                  <span>Created {relativeTime(t.createdAt, now)}</span><span aria-hidden="true">·</span>
                  <span>{t.lastUsedAt ? `last used ${relativeTime(t.lastUsedAt, now)}` : "never used"}</span><span aria-hidden="true">·</span>
                  {new Date(t.expiresAt).getTime() <= now ? <Badge tone="danger" className="h-5 px-1.5 text-[11px]">Expired</Badge> : <span>expires {relativeTime(t.expiresAt, now)}</span>}
                </div>
              </div>
              <Button variant="destructive" className="min-h-11 w-full md:hidden" onClick={() => setRevoking(t)}><Trash2 className="size-4" strokeWidth={1.75} /> Revoke</Button>
              <button type="button" aria-label={`Revoke ${t.name}`} onClick={() => setRevoking(t)} className="hidden size-11 shrink-0 items-center justify-center self-end rounded-[7px] md:flex text-secondary transition-colors hover:bg-surface-hover hover:text-foreground sm:size-8 sm:self-auto"><Trash2 className="size-4" strokeWidth={1.75} /></button>
            </li>
          ))}
        </ul>
      )}
      {error && <div className="border-t border-border px-6 py-3 text-sm">{error}</div>}
      <ConfirmDialog
        open={!!revoking}
        onClose={() => setRevoking(null)}
        title={`Revoke ${revoking?.name ?? "token"}?`}
        description="The CLI or MCP server using it stops working immediately."
        confirmLabel="Revoke token"
        danger
        pending={pending}
        onConfirm={() => start(async () => { if (!revoking) return; const r = await revokeApiToken(revoking.id); setRevoking(null); if (r.ok) router.refresh(); else setError(r.error); })}
      />
    </Card>
  );
}
