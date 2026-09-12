"use client";

import { RefreshCw } from "lucide-react";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";
import { syncApp } from "../actions";

export function SyncButton({ projectId, registryId }: { projectId: string; registryId: string }) {
  const [pending, start] = useTransition();
  return (
    <Button variant="outline" size="sm" disabled={pending} onClick={() => start(() => syncApp(projectId, registryId))} title="git fetch + pull">
      <RefreshCw className={pending ? "size-4 animate-spin" : "size-4"} /> Sync
    </Button>
  );
}
