"use client";

import { Logo } from "@/components/logo";

import { useRouter } from "next/navigation";
import { useActionState, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { slugify } from "@/lib/utils";
import { createOrganization } from "./actions";

export function OrgForm({ first }: { first: boolean }) {
  const router = useRouter();
  const [state, action, pending] = useActionState(createOrganization, null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (state && state.error === undefined) {
      router.push("/projects");
      router.refresh();
    }
  }, [state, router]);

  return (
    <Card className="w-full max-w-md">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform</div>
        <div>
          <h1 className="text-lg font-semibold">{first ? "Create your organization" : "New organization"}</h1>
          <p className="text-sm text-secondary">Organizations own projects; projects group apps.</p>
        </div>
        <form method="post" action={action} className="space-y-3">
          <Field label="Name">
            <Input name="name" value={name} onChange={(e) => { setName(e.target.value); if (!touched) setSlug(slugify(e.target.value)); }} placeholder="Acme" required autoFocus />
          </Field>
          <Field label="Slug" hint="Used in URLs and the CLI.">
            <Input name="slug" className="font-mono" value={slug} onChange={(e) => { setTouched(true); setSlug(slugify(e.target.value)); }} required />
          </Field>
          {state?.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{state.error}</div>}
          <div className="flex justify-end gap-2">
            {!first && <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>}
            <Button type="submit" disabled={pending || !name}>{pending ? "Creating…" : "Create organization"}</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
