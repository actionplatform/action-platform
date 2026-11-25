import { Badge } from "@/components/ui/badge";
import { Hint } from "@/components/ui/hint";
import type { Verdict } from "@/lib/releases";

const TONE: Record<Verdict, "success" | "danger" | "neutral"> = { ok: "success", blocked: "danger", pending: "neutral" };
const LABEL: Record<Verdict, string> = { ok: "ready", blocked: "blocked", pending: "checking" };

export function verdictOf(readiness: Record<string, Verdict>, stage: string): Verdict | null {
  return readiness[stage] ?? null;
}

const ORDER: Verdict[] = ["blocked", "pending", "ok"];

export function ReadinessSummary({ readiness }: { readiness: Record<string, Verdict> }) {
  const stages = Object.keys(readiness).sort();
  if (stages.length === 0) return <span className="text-secondary">—</span>;
  const counts = ORDER.map((v) => ({ verdict: v, count: stages.filter((s) => readiness[s] === v).length })).filter((c) => c.count > 0);
  const label = `${stages.length} ${stages.length === 1 ? "scope" : "scopes"}: ${counts.map((c) => `${c.count} ${LABEL[c.verdict]}`).join(", ")}`;
  return (
    <Hint
      text={label}
      pinnable
      className="max-w-full"
      content={
        <span className="flex flex-col gap-1">
          {stages.map((s) => (
            <span key={s} className="flex items-center justify-between gap-3">
              <span className="break-all font-mono text-foreground">{s}</span>
              <Badge tone={TONE[readiness[s]]} className="h-5 shrink-0 px-1.5 text-[11px]">{LABEL[readiness[s]]}</Badge>
            </span>
          ))}
        </span>
      }
    >
      <button type="button" aria-label={label} className="inline-flex flex-nowrap items-center gap-1 whitespace-nowrap rounded focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
        {counts.map((c) => (
          <Badge key={c.verdict} tone={TONE[c.verdict]} className="h-5 shrink-0 whitespace-nowrap px-1.5 text-[11px]">{c.count} {LABEL[c.verdict]}</Badge>
        ))}
      </button>
    </Hint>
  );
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
