"use client";

import { Puzzle, SearchX, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";

function Shell({ icon, title, text, children }: { icon: React.ReactNode; title: string; text: string; children?: React.ReactNode }) {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center rounded-[9px] border border-dashed border-border px-6 text-center">
      {icon}
      <h2 className="mt-4 text-[17px] font-semibold">{title}</h2>
      <p className="mt-1 max-w-sm text-sm text-secondary">{text}</p>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}

export function PluginsNoneState() {
  return <Shell icon={<Puzzle className="size-6 text-secondary" strokeWidth={1.5} />} title="No plugins published" text="The index has no plugins yet." />;
}

export function PluginsNoResults({ onClear }: { onClear: () => void }) {
  return (
    <Shell icon={<SearchX className="size-6 text-secondary" strokeWidth={1.5} />} title="No plugins found" text="No plugins match your search.">
      <Button variant="outline" onClick={onClear}>Clear</Button>
    </Shell>
  );
}

export function PluginsErrorState() {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <Shell icon={<TriangleAlert className="size-6 text-secondary" strokeWidth={1.5} />} title="Index unavailable" text="The plugins index could not be read. It is served from GitHub; try again in a moment.">
      <Button variant="outline" disabled={pending} onClick={() => start(() => router.refresh())}>{pending ? "Retrying…" : "Retry"}</Button>
    </Shell>
  );
}
