"use client";

import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/logo";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { resetPassword } from "@/lib/auth-actions";

const MIN = 8;

export function ResetPasswordForm({ token }: { token: string }) {
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const f = new FormData(e.currentTarget);
    const password = String(f.get("password"));
    if (password !== String(f.get("confirm"))) return setError("the passwords do not match");
    setBusy(true);
    const res = await resetPassword(token, password);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    setDone(true);
  }

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        {done ? (
          <>
            <p className="text-sm">Your password was changed and every open session was signed out.</p>
            <Link href="/login" className={cn(buttonVariants(), "w-full")}>Sign in</Link>
          </>
        ) : (
          <form method="post" onSubmit={submit} className="space-y-3">
            <p className="text-sm text-muted-foreground">Choose a new password, at least {MIN} characters.</p>
            <Field name="password" label="New password" />
            <Field name="confirm" label="Repeat the new password" />
            {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
            <Button type="submit" className="w-full" disabled={busy}>Change password</Button>
            <div className="text-center text-xs">
              <Link href="/forgot-password" className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline">Ask for a new link</Link>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ name, label }: { name: string; label: string }) {
  return (
    <label className="block text-sm">
      <span className="text-muted-foreground text-xs">{label}</span>
      <input name={name} type="password" required minLength={MIN} autoComplete="new-password" className="mt-1 w-full h-9 rounded-md border border-border bg-background px-3" />
    </label>
  );
}
