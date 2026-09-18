"use client";

import { LogOut, Monitor, Smartphone, Terminal, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { ConfirmDialog } from "@/components/ui/dialog";
import { describeAgent } from "@/lib/user-agent";
import { relativeTime } from "@/lib/time";
import { revokeBrowserSession } from "./actions";

type Row = { id: string; createdAt: Date; updatedAt: Date; expiresAt: Date; ipAddress: string | null; userAgent: string | null; current: boolean };

export function SessionsCard({ sessions, now }: { sessions: Row[]; now: number }) {
  const router = useRouter();
  const [revoking, setRevoking] = useState<Row | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Panel>
      <PanelHeader title="Browser sessions" description="Where this account is signed in. Signing out a session logs that browser out immediately." />
      <ul className="divide-y divide-border-subtle">
        {sessions.map((s) => {
          const agent = describeAgent(s.userAgent);
          const mobile = agent.os === "iOS" || agent.os === "Android";
          const cli = /cli|curl|python|node|go-http|action-platform/i.test(s.userAgent ?? "") && !agent.os;
          const Icon = cli ? Terminal : mobile ? Smartphone : Monitor;
          return (
            <li key={s.id} className="flex items-center gap-3 px-4 py-3 md:px-6 md:py-4">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] border border-border bg-background">
                <Icon className="size-4 text-secondary" strokeWidth={1.75} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium">{agent.browser}{agent.os ? ` on ${agent.os}` : ""}</span>
                  {s.current && <Badge tone="inverse" className="h-5 px-2 text-[11px]">This browser</Badge>}
                </div>
                <div className="mt-0.5 line-clamp-2 text-[13px] text-secondary md:truncate" suppressHydrationWarning>{s.ipAddress ?? "Unknown address"} · Active {relativeTime(s.updatedAt, now)}<span className="hidden md:inline"> · signed in {relativeTime(s.createdAt, now)}</span></div>
              </div>
              {!s.current && <Button variant="outline" className="min-h-11 shrink-0 md:hidden" onClick={() => setRevoking(s)}><LogOut className="size-4" strokeWidth={1.75} /> Sign out</Button>}
              {!s.current && <button type="button" aria-label="Sign out this session" onClick={() => setRevoking(s)} className="hidden size-11 shrink-0 items-center justify-center rounded-[7px] md:flex text-secondary transition-colors hover:bg-surface-hover hover:text-foreground sm:size-8"><Trash2 className="size-4" strokeWidth={1.75} /></button>}
            </li>
          );
        })}
      </ul>
      {error && <div className="border-t border-border px-6 py-3 text-sm">{error}</div>}
      <ConfirmDialog
        open={!!revoking}
        onClose={() => setRevoking(null)}
        title="Sign out this session?"
        description="That browser is logged out at once and has to sign in again."
        confirmLabel="Sign out"
        danger
        pending={pending}
        onConfirm={() => start(async () => { if (!revoking) return; const r = await revokeBrowserSession(revoking.id); setRevoking(null); if (r.ok) router.refresh(); else setError(r.error); })}
      />
    </Panel>
  );
}
