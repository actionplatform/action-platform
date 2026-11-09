"use client";

import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { requestPasswordReset } from "@/lib/auth-actions";

export function ForgotPasswordForm() {
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const email = String(new FormData(e.currentTarget).get("email"));
    const res = await requestPasswordReset(email);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    setSent(email);
  }

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        {sent ? (
          <p className="text-sm">
            If <span className="font-medium">{sent}</span> has an account, a link to reset its password is on its way. It works for 30 minutes.
          </p>
        ) : (
          <form method="post" onSubmit={submit} className="space-y-3">
            <p className="text-sm text-muted-foreground">Enter your email and we will send you a link to choose a new password.</p>
            <label className="block text-sm">
              <span className="text-muted-foreground text-xs">Email</span>
              <input name="email" type="email" required autoComplete="email" className="mt-1 w-full h-9 rounded-md border border-border bg-background px-3" />
            </label>
            {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
            <Button type="submit" className="w-full" disabled={busy}>Send reset link</Button>
          </form>
        )}
        <div className="text-center text-xs">
          <Link href="/login" className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline">Back to sign in</Link>
        </div>
      </CardContent>
    </Card>
  );
}
