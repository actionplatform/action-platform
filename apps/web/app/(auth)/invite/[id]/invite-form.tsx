"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { GoogleButton } from "@/components/google-button";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { signIn, signOut } from "@/lib/auth-actions";
import { acceptInvite, joinWithNewAccount } from "./actions";

type Invitation = { id: string; email: string | null; login: string | null; host: string | null; role: string; org: string; inviter: string };

const HOSTS: Record<string, string> = { github: "GitHub", gitlab: "GitLab", bitbucket: "Bitbucket" };

export function InviteForm({ invitation, mode, currentEmail, google = false, problem = null }: { invitation: Invitation; mode: "accept" | "mismatch" | "join" | "verify"; currentEmail: string | null; google?: boolean; problem?: string | null }) {
  const router = useRouter();
  const [tab, setTab] = useState<"signup" | "signin">("signup");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(problem);
  const host = HOSTS[invitation.host ?? ""] ?? invitation.host ?? "the code host";
  const verifyUrl = `/api/invitations/${encodeURIComponent(invitation.id)}/verify`;
  const byLogin = !!invitation.login;
  const [pending, start] = useTransition();

  const finish = (r: { ok: true } | { ok: false; error: string }) => {
    if (!r.ok) setError(r.error);
    else if (byLogin) window.location.assign(verifyUrl);
    else { router.push("/projects"); router.refresh(); }
  };

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        <div>
          <h1 className="text-lg font-semibold">Join {invitation.org}</h1>
          <p className="mt-1 text-sm text-secondary">{invitation.inviter} invited <span className="text-foreground">{byLogin ? `@${invitation.login} on ${host}` : invitation.email}</span> as {invitation.role}.</p>
          {byLogin && <p className="mt-1 text-sm text-secondary">Sign in or create an account, then verify the {host} account to join.</p>}
        </div>

        {mode === "verify" && (
          <div className="space-y-3">
            <p className="text-sm text-secondary">Signed in as {currentEmail}.</p>
            <a href={verifyUrl} className="block"><Button className="w-full">Verify @{invitation.login} on {host} and join</Button></a>
          </div>
        )}

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
            {google && !byLogin && <GoogleButton next={`/invite/${invitation.id}`} label={`Join with Google as ${invitation.email}`} />}
            <div className="flex gap-1 rounded-md border border-border p-1 text-sm">
              <button type="button" onClick={() => setTab("signup")} className={`flex-1 rounded px-2 py-1 ${tab === "signup" ? "bg-surface-hover text-foreground" : "text-secondary"}`}>Create account</button>
              <button type="button" onClick={() => setTab("signin")} className={`flex-1 rounded px-2 py-1 ${tab === "signin" ? "bg-surface-hover text-foreground" : "text-secondary"}`}>I have an account</button>
            </div>
            {byLogin ? <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field> : <Field label="Email"><Input value={invitation.email ?? ""} readOnly className="text-secondary" /></Field>}
            {tab === "signup" && <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} autoFocus /></Field>}
            <Field label="Password"><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus={tab === "signin"} /></Field>
            <Button
              className="w-full"
              disabled={pending || !password || (tab === "signup" && !name.trim()) || (byLogin && !email.trim())}
              onClick={() => start(async () => {
                setError(null);
                if (tab === "signup") return finish(await joinWithNewAccount(invitation.id, name, password, email));
                const res = await signIn(invitation.email ?? email.trim(), password);
                if (!res.ok) return setError(res.error);
                finish(byLogin ? { ok: true } : await acceptInvite(invitation.id));
              })}
            >
              {pending ? "Joining…" : byLogin ? (tab === "signup" ? `Create account and verify on ${host}` : `Sign in and verify on ${host}`) : tab === "signup" ? "Create account and join" : "Sign in and join"}
            </Button>
          </div>
        )}

        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </CardContent>
    </Card>
  );
}
