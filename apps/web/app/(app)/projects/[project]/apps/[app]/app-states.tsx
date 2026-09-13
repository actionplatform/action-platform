"use client";

import { TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";

export function AppErrorState({ name, projectId }: { name: string; projectId: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[9px] border border-dashed border-border px-6 text-center">
      <TriangleAlert className="size-6 text-secondary" strokeWidth={1.5} />
      <h1 className="mt-4 text-[17px] font-semibold">Couldn’t load project</h1>
      <p className="mt-1 max-w-sm text-sm text-secondary">Something went wrong while loading {name}.</p>
      <div className="mt-6 flex gap-2">
        <Button disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? "Retrying…" : "Try again"}</Button>
        <Link href={`/projects/${projectId}`}><Button variant="outline">Back to projects</Button></Link>
      </div>
    </div>
  );
}
