"use client";

import { Logo } from "@/components/logo";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { signIn } from "@/lib/auth-actions";

export function LoginForm({ next = "/projects" }: { next?: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
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
        <form onSubmit={submit} className="space-y-3">
          <Field name="email" label="Email" type="email" />
          <Field name="password" label="Password" type="password" />
          {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
          <Button type="submit" className="w-full" disabled={busy}>Sign in</Button>
        </form>
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
