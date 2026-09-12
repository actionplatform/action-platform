"use client";

import { Plus } from "lucide-react";
import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { addApp } from "./actions";

export function AddForm({ projectId }: { projectId: string }) {
  const [state, action, pending] = useActionState(addApp.bind(null, projectId), null);

  return (
    <form action={action} className="space-y-2">
      <div className="text-xs text-secondary">Add an existing repository</div>
      <div className="flex gap-2">
        <input name="url" placeholder="https://github.com/org/repo.git" className="flex-1 h-9 px-3 text-sm font-mono" required />
        <Button type="submit" variant="outline" disabled={pending}><Plus className="size-4" /> {pending ? "Cloning…" : "Add"}</Button>
      </div>
      {state?.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{state.error}</div>}
    </form>
  );
}
