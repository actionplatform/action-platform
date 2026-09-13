"use client";

import { TriangleAlert, Wrench } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { reinstallPlatform } from "../actions";

export function AppErrorState({ name, projectId, registryId, reason, missingManifest }: { name: string; projectId: string; registryId: string; reason: string | null; missingManifest: boolean }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[9px] border border-dashed border-border px-6 text-center">
      <TriangleAlert className="size-6 text-secondary" strokeWidth={1.5} />
      <h1 className="mt-4 text-[17px] font-semibold">{missingManifest ? "This repository has no platform.toml" : "Couldn’t load project"}</h1>
      <p className="mt-1 max-w-md text-sm text-secondary">{missingManifest ? `${name} was imported without the platform files, or they were discarded before being committed. Install them again to continue.` : `Something went wrong while loading ${name}.`}</p>
      {reason && !missingManifest && <p className="mt-2 max-w-md font-mono text-xs text-muted-foreground">{reason}</p>}
      <div className="mt-6 flex gap-2">
        {missingManifest && <Button disabled={pending} onClick={() => start(async () => { setError(null); const r = await reinstallPlatform(projectId, registryId); if (r.ok) router.refresh(); else setError(r.error); })}><Wrench className="size-4" strokeWidth={1.75} /> {pending ? "Installing…" : "Install platform files"}</Button>}
        <Button variant={missingManifest ? "outline" : "default"} disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? "Retrying…" : "Try again"}</Button>
        <Link href={`/projects/${projectId}`}><Button variant="outline">Back to project</Button></Link>
      </div>
      {error && <div className="mt-4 rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
    </div>
  );
}
