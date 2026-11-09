"use client";

import { GoogleButton } from "@/components/google-button";
import { Logo } from "@/components/logo";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { signIn } from "@/lib/auth-actions";

export function LoginForm({ next = "/projects", recovery = false, google = false, initialError = null }: { next?: string; recovery?: boolean; google?: boolean; initialError?: string | null }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(initialError);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const f = new FormData(e.currentTarget);
    const email = String(f.get("email"));
    const password = String(f.get("password"));
    const res = await signIn(email, password);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    router.push(next);
    router.refresh();
  }

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        {google && (
          <>
            <GoogleButton next={next} />
            <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or<span className="h-px flex-1 bg-border" /></div>
          </>
        )}
        <form method="post" onSubmit={submit} className="space-y-3">
          <Field name="email" label="Email" type="email" />
          <Field name="password" label="Password" type="password" />
          {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
          <Button type="submit" className="w-full" disabled={busy}>Sign in</Button>
        </form>
        {recovery && (
          <div className="text-center text-xs">
            <Link href="/forgot-password" className="text-muted-foreground hover:text-foreground underline-offset-4 hover:underline">Forgot your password?</Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ name, label, type = "text" }: { name: string; label: string; type?: string }) {
  return (
    <label className="block text-sm">
      <span className="text-muted-foreground text-xs">{label}</span>
      <input name={name} type={type} required className="mt-1 w-full h-9 rounded-md border border-border bg-background px-3" />
    </label>
  );
}
