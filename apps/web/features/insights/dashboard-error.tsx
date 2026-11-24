"use client";

import { TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";

export function DashboardError({ reason }: { reason: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <div role="alert" className="flex min-h-[320px] flex-col items-center justify-center rounded-[10px] border border-dashed border-border px-6 text-center">
      <TriangleAlert className="size-6 text-secondary" strokeWidth={1.5} aria-hidden />
      <h2 className="mt-4 text-[17px] font-semibold">Couldn’t load the dashboard</h2>
      <p className="mt-1 max-w-md text-sm text-secondary">{reason}</p>
      <Button className="mt-6" disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? "Retrying…" : "Try again"}</Button>
    </div>
  );
}
