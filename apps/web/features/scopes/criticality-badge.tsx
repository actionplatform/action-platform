import { Badge } from "@/components/ui/badge";
import { CRITICALITY, type Criticality } from "@/lib/scope-kinds";

export function CriticalityBadge({ value, className }: { value: string; className?: string }) {
  const meta = CRITICALITY[value as Criticality] ?? { label: value, tone: "neutral" as const, hint: "" };
  return <Badge tone={meta.tone} title={meta.hint} className={className}>{meta.label}</Badge>;
}
