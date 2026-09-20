import { Badge } from "@/components/ui/badge";
import type { Verdict } from "@/lib/releases";

const TONE: Record<Verdict, "success" | "danger" | "neutral"> = { ok: "success", blocked: "danger", pending: "neutral" };
const LABEL: Record<Verdict, string> = { ok: "ready", blocked: "blocked", pending: "checking" };

export function verdictOf(readiness: Record<string, Verdict>, stage: string): Verdict | null {
  return readiness[stage] ?? null;
}

export function ReadinessBadges({ readiness, compact = false }: { readiness: Record<string, Verdict>; compact?: boolean }) {
  const stages = Object.keys(readiness).sort();
  if (stages.length === 0) return <span className="text-secondary">—</span>;
  return (
    <span className="flex flex-wrap items-center gap-1">
      {stages.map((s) => (
        <Badge key={s} tone={TONE[readiness[s]]} className="h-5 max-w-full gap-1 px-1.5 font-mono text-[11px]" title={`${s}: ${LABEL[readiness[s]]}`}>
          <span className="truncate">{s}</span>{!compact && <span className="shrink-0 font-sans">· {LABEL[readiness[s]]}</span>}
        </Badge>
      ))}
    </span>
  );
}
