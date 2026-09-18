import { Ban, Check, CircleDashed, Clock, HelpCircle, LoaderCircle, TriangleAlert, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { CiRunStatus } from "@/lib/ci-kinds";

const META: Record<CiRunStatus, { label: string; tone: "success" | "danger" | "warning" | "neutral"; icon: typeof Check; spin?: boolean }> = {
  success: { label: "Passed", tone: "success", icon: Check },
  failure: { label: "Failed", tone: "danger", icon: X },
  unstable: { label: "Unstable", tone: "warning", icon: TriangleAlert },
  aborted: { label: "Aborted", tone: "neutral", icon: Ban },
  running: { label: "Running", tone: "neutral", icon: LoaderCircle, spin: true },
  queued: { label: "Queued", tone: "neutral", icon: Clock },
  unknown: { label: "Unknown", tone: "neutral", icon: HelpCircle },
};

export function RunBadge({ status, className }: { status: CiRunStatus; className?: string }) {
  const meta = META[status] ?? META.unknown;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} className={`h-5 gap-1 px-2 text-[11px] ${className ?? ""}`}>
      <Icon className={`size-3 ${meta.spin ? "animate-spin" : ""}`} strokeWidth={2.5} /> {meta.label}
    </Badge>
  );
}

export function RunIcon({ status }: { status: CiRunStatus }) {
  const meta = META[status] ?? META.unknown;
  const Icon = status === "queued" || status === "unknown" ? CircleDashed : meta.icon;
  const color = status === "success" ? "text-status-ok" : status === "failure" ? "text-status-bad" : status === "unstable" ? "text-status-warn" : "text-secondary";
  return <Icon className={`size-4 shrink-0 ${color} ${meta.spin ? "animate-spin" : ""}`} strokeWidth={1.75} />;
}
