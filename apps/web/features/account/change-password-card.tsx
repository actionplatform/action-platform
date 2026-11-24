"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { changePassword } from "./actions";

const MIN = 8;

export function ChangePasswordCard() {
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pending, start] = useTransition();

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const next = String(f.get("next"));
    setError(null);
    setDone(false);
    if (next !== String(f.get("confirm"))) return setError("the new passwords do not match");
    start(async () => {
      const r = await changePassword(String(f.get("current")), next);
      if (!r.ok) return setError(r.error);
      form.reset();
      setDone(true);
    });
  }

  return (
    <Panel>
      <PanelHeader title="Password" description="Changing it signs out every other browser session and revokes every API token, so the CLI and the MCP servers signed in as you have to log in again. This browser stays signed in." />
      <PanelBody>
        <form onSubmit={submit} className="grid max-w-sm gap-3">
          <Field label="Current password">
            <Input name="current" type="password" required autoComplete="current-password" disabled={pending} />
          </Field>
          <Field label="New password" hint={`At least ${MIN} characters`}>
            <Input name="next" type="password" required minLength={MIN} autoComplete="new-password" disabled={pending} />
          </Field>
          <Field label="Repeat the new password">
            <Input name="confirm" type="password" required minLength={MIN} autoComplete="new-password" disabled={pending} />
          </Field>
          {error && <div className="rounded-[8px] border border-foreground px-3 py-2 text-sm" role="alert">{error}</div>}
          {done && <div className="rounded-[8px] border border-border px-3 py-2 text-sm" role="status">Password changed. Other sessions and API tokens were signed out.</div>}
          <div>
            <Button type="submit" disabled={pending}>Change password</Button>
          </div>
        </form>
      </PanelBody>
    </Panel>
  );
}
