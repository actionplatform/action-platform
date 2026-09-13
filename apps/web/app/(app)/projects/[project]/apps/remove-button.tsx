"use client";

import { Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { removeApp } from "./actions";

export function RemoveButton({ projectId, appId, name }: { projectId: string; appId: string; name: string }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();

  return (
    <>
      <Button variant="ghost" size="icon" title="Remove app" aria-label={`Remove ${name}`} onClick={() => setOpen(true)} className="size-11 shrink-0 md:size-8"><Trash2 className="size-4" /></Button>
      <ConfirmDialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Remove ${name}?`}
        description="The platform's clone is deleted. The repository is untouched."
        confirmLabel="Remove app"
        danger
        pending={pending}
        onConfirm={() => start(async () => { await removeApp(projectId, appId); setOpen(false); })}
      />
    </>
  );
}
