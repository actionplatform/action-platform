"use client";

import { Plus } from "lucide-react";
import { useActionState, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { newProject } from "./actions";

export function NewProjectForm() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="lg" onClick={() => setOpen(true)}><Plus className="size-4" strokeWidth={2} /> New project</Button>
      <NewProjectDialog open={open} onClose={() => setOpen(false)} />
    </>
  );
}

export function NewProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [state, action, pending] = useActionState(newProject, null);

  useEffect(() => {
    if (state && state.error === undefined) onClose();
  }, [state, onClose]);

  return (
    <Dialog open={open} onClose={onClose} title="New project" description="A project groups apps that ship together.">
      <form action={action} className="space-y-3">
        <Field label="Name"><Input name="name" placeholder="Orders platform" required autoFocus /></Field>
        <Field label="Description"><Input name="description" placeholder="What ships from here" /></Field>
        {state?.error && <div className="rounded-md border border-foreground px-3 py-2 text-sm text-foreground">{state.error}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={pending}>{pending ? "Creating…" : "Create project"}</Button>
        </div>
      </form>
    </Dialog>
  );
}
