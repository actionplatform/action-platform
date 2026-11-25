import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Protection } from "@/lib/protection";
import { summaryOf } from "./model";

export function ProtectionSummary({ protection, settingsHref }: { protection: Protection | null; settingsHref: string }) {
  const s = summaryOf(protection);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border px-4 py-2.5 text-sm">
      <ShieldCheck className="size-4 shrink-0 text-secondary" strokeWidth={1.75} aria-hidden />
      <span className="text-xs text-muted-foreground">On the code host</span>
      <Badge tone={s.tone}>{s.label}</Badge>
      <span className="min-w-0 flex-1 truncate text-[13px] text-secondary" title={s.detail}>{s.detail}</span>
      <Link href={settingsHref} className="text-[13px] text-foreground underline-offset-4 hover:underline">Settings</Link>
    </div>
  );
}
