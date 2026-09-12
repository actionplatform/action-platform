"use client";

import { Plus } from "lucide-react";
import { useActionState, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { newProject } from "./actions";

export function NewProjectForm() {
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState(newProject, null);

  useEffect(() => {
    if (state && state.error === undefined) setOpen(false);
  }, [state]);

  return (
    <>
      <Button onClick={() => setOpen(true)}><Plus className="size-4" /> New project</Button>
      <Dialog open={open} onClose={() => setOpen(false)} title="New project" description="A project groups apps that ship together.">
        <form action={action} className="space-y-3">
          <Field label="Name"><Input name="name" placeholder="Orders platform" required autoFocus /></Field>
          <Field label="Description"><Input name="description" placeholder="What ships from here" /></Field>
          {state?.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{state.error}</div>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={pending}>{pending ? "Creating…" : "Create project"}</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
