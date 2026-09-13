"use client";

import { KeyRound, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import type { ApiToken } from "@/lib/api-tokens";
import { SCOPE_INFO } from "@/lib/permissions";
import { relativeTime } from "@/lib/time";
import { revokeApiToken } from "./actions";

export function TokensCard({ tokens, now }: { tokens: ApiToken[]; now: number }) {
  const router = useRouter();
  const [revoking, setRevoking] = useState<ApiToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Card className="rounded-[11px]">
      <header className="border-b border-border px-6 py-5">
        <h2 className="text-[15px] font-semibold">Your API tokens</h2>
        <p className="mt-1 text-[13px] text-secondary">Bearer tokens issued to the CLI and MCP servers by <code className="font-mono">action-platform login</code>. Each carries a scope on top of your role; revoke what you no longer use.</p>
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
            <li key={t.id} className="flex flex-col gap-2 px-6 py-4 sm:flex-row sm:items-center sm:gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium">{t.name}</span>
                  {t.scope.map((s) => <Badge key={s} className="h-5 px-2 text-[11px]">{SCOPE_INFO[s].label}</Badge>)}
                </div>
                <div className="mt-0.5 text-[13px] text-secondary">Created {relativeTime(t.createdAt, now)} · {t.lastUsedAt ? `last used ${relativeTime(t.lastUsedAt, now)}` : "never used"} · expires {relativeTime(t.expiresAt, now)}</div>
              </div>
              <button type="button" aria-label={`Revoke ${t.name}`} onClick={() => setRevoking(t)} className="flex size-11 shrink-0 items-center justify-center self-end rounded-[7px] text-secondary transition-colors hover:bg-surface-hover hover:text-foreground sm:size-8 sm:self-auto"><Trash2 className="size-4" strokeWidth={1.75} /></button>
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
