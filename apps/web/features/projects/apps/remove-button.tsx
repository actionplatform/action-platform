"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DeleteAppDialog } from "@/features/projects";

export function RemoveButton({ projectId, appId, name, repositoryUrl = null }: { projectId: string; appId: string; name: string; repositoryUrl?: string | null }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  return (
    <>
      <Button variant="ghost" size="icon" title="Remove app" aria-label={`Remove ${name}`} onClick={() => setOpen(true)} className="size-11 shrink-0 md:size-8"><Trash2 className="size-4" /></Button>
      <DeleteAppDialog open={open} onClose={() => setOpen(false)} onDeleted={(queued) => { setOpen(false); if (queued) router.push(`/projects/${projectId}/apps/${appId}/deployments`); else router.refresh(); }} projectId={projectId} appId={appId} name={name} repositoryUrl={repositoryUrl} />
    </>
  );
}
