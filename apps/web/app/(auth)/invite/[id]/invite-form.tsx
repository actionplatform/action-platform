"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { signIn, signOut } from "@/lib/auth-actions";
import { acceptInvite, joinWithNewAccount } from "./actions";

type Invitation = { id: string; email: string; role: string; org: string; inviter: string };

export function InviteForm({ invitation, mode, currentEmail }: { invitation: Invitation; mode: "accept" | "mismatch" | "join"; currentEmail: string | null }) {
  const router = useRouter();
  const [tab, setTab] = useState<"signup" | "signin">("signup");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const finish = (r: { ok: true } | { ok: false; error: string }) => {
    if (r.ok) { router.push("/projects"); router.refresh(); } else setError(r.error);
  };

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        <div>
          <h1 className="text-lg font-semibold">Join {invitation.org}</h1>
          <p className="mt-1 text-sm text-secondary">{invitation.inviter} invited <span className="text-foreground">{invitation.email}</span> as {invitation.role}.</p>
        </div>

        {mode === "accept" && (
          <Button className="w-full" disabled={pending} onClick={() => start(async () => { setError(null); finish(await acceptInvite(invitation.id)); })}>{pending ? "Joining…" : `Join as ${currentEmail}`}</Button>
        )}

        {mode === "mismatch" && (
          <div className="space-y-3">
            <p className="text-sm text-secondary">You are signed in as {currentEmail}. Sign out and use the invited address.</p>
            <Button variant="outline" className="w-full" disabled={pending} onClick={() => start(async () => { await signOut(); router.refresh(); })}>Sign out</Button>
          </div>
        )}

        {mode === "join" && (
          <div className="space-y-3">
            <div className="flex gap-1 rounded-md border border-border p-1 text-sm">
              <button type="button" onClick={() => setTab("signup")} className={`flex-1 rounded px-2 py-1 ${tab === "signup" ? "bg-surface-hover text-foreground" : "text-secondary"}`}>Create account</button>
              <button type="button" onClick={() => setTab("signin")} className={`flex-1 rounded px-2 py-1 ${tab === "signin" ? "bg-surface-hover text-foreground" : "text-secondary"}`}>I have an account</button>
            </div>
            <Field label="Email"><Input value={invitation.email} readOnly className="text-secondary" /></Field>
            {tab === "signup" && <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} autoFocus /></Field>}
            <Field label="Password"><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus={tab === "signin"} /></Field>
            <Button
              className="w-full"
              disabled={pending || !password || (tab === "signup" && !name.trim())}
              onClick={() => start(async () => {
                setError(null);
                if (tab === "signup") return finish(await joinWithNewAccount(invitation.id, name, password));
                const res = await signIn(invitation.email, password);
                if (!res.ok) return setError(res.error);
                finish(await acceptInvite(invitation.id));
              })}
            >
              {pending ? "Joining…" : tab === "signup" ? "Create account and join" : "Sign in and join"}
            </Button>
          </div>
        )}

        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </CardContent>
    </Card>
  );
}
