import { Boxes, Cloud, GitBranch, Package, Tag, Workflow, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { ciLabel, sourceLabel, type AppView } from "./model";
import { targetsOf } from "@/features/deployments";

function Row({ icon: Icon, label, value, mono, muted }: { icon: LucideIcon; label: string; value: string; mono?: boolean; muted?: boolean }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 text-sm">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
      <span className="w-24 shrink-0 text-secondary">{label}</span>
      <span className={`min-w-0 break-words ${mono ? "font-mono text-[13px]" : ""} ${muted ? "text-muted-foreground" : ""}`}>{value}</span>
    </div>
  );
}

export function SourceCard({ view, base }: { view: AppView; base: string }) {
  const release = [view.releaseStrategy === "semver" ? "SemVer" : view.releaseStrategy, view.commitConvention === "conventional" ? "Conventional Commits" : view.commitConvention].filter(Boolean).join(" · ");
  const deploy = targetsOf(view.deploy);
  return (
    <Panel>
      <PanelHeader title="Source & automation" aside={<Link href={`${base}/configuration`} className="text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">Open configuration</Link>} />
      <div className="divide-y divide-border-subtle py-1">
        <Row icon={GitBranch} label="Source" value={sourceLabel(view.sourceKind)} muted={!view.sourceKind} />
        <Row icon={Package} label="Repository" value={view.repository ?? "None"} mono={!!view.repository} muted={!view.repository} />
        <Row icon={Tag} label="Release" value={release || "Not configured"} muted={!release} />
        <Row icon={Workflow} label="CI" value={ciLabel(view.ci) ?? "Not configured"} muted={!view.ci} />
        <Row icon={Cloud} label="Deploy target" value={deploy ?? "Not configured"} mono={!!deploy} muted={!deploy} />
        <Row icon={Boxes} label="Services" value={view.services.length ? view.services.join(", ") : "No services"} mono={view.services.length > 0} muted={view.services.length === 0} />
      </div>
    </Panel>
  );
}
