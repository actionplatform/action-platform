"use client";

import { Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { removeProject } from "./actions";

export function RemoveProjectButton({ id, name }: { id: string; name: string }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();

  return (
    <>
      <Button variant="ghost" size="icon" title="Delete project" onClick={() => setOpen(true)}><Trash2 className="size-4" /></Button>
      <ConfirmDialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Delete ${name}?`}
        description="Every app in it is removed and the platform's clones are deleted. The repositories themselves are untouched."
        confirmLabel="Delete project"
        danger
        pending={pending}
        onConfirm={() => start(async () => { await removeProject(id); setOpen(false); })}
      />
    </>
  );
}
