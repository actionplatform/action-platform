"use client";

import { LayoutTemplate, SearchX, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";

function Shell({ icon, title, text, children }: { icon: React.ReactNode; title: string; text: string; children?: React.ReactNode }) {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center rounded-lg border border-dashed border-border px-6 text-center">
      {icon}
      <h2 className="mt-4 text-[17px] font-semibold">{title}</h2>
      <p className="mt-1 max-w-sm text-sm text-secondary">{text}</p>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}

export function TemplatesNoneState() {
  return <Shell icon={<LayoutTemplate className="size-6 text-secondary" strokeWidth={1.5} />} title="No templates available" text="Templates will appear here when they are available." />;
}

export function TemplatesNoResults({ onClear }: { onClear: () => void }) {
  return (
    <Shell icon={<SearchX className="size-6 text-secondary" strokeWidth={1.5} />} title="No templates found" text="No templates match your current filters.">
      <Button variant="outline" onClick={onClear}>Clear filters</Button>
    </Shell>
  );
}

export function TemplatesErrorState() {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Shell icon={<TriangleAlert className="size-6 text-secondary" strokeWidth={1.5} />} title="Couldn’t load templates" text="Something went wrong while loading the template catalog.">
      <Button variant="outline" disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? "Retrying…" : "Try again"}</Button>
    </Shell>
  );
}
