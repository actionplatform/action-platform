import { Boxes, GitBranch, Package, Workflow, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { ciLabel, sourceLabel, type AppView } from "./model";
import { NameChips } from "@/components/ui/name-chips";

function Row({ icon: Icon, label, value, mono, muted, names, noun }: { icon: LucideIcon; label: string; value?: string; mono?: boolean; muted?: boolean; names?: string[]; noun?: string }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 text-sm">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
      <span className="w-24 shrink-0 text-secondary">{label}</span>
      {names && names.length > 0 && noun ? (
        <NameChips names={names} noun={noun} max={3} />
      ) : (
        <span className={`min-w-0 break-words ${mono ? "font-mono text-[13px]" : ""} ${muted ? "text-muted-foreground" : ""}`}>{value}</span>
      )}
    </div>
  );
}

export function SourceCard({ view, base }: { view: AppView; base: string }) {
  return (
    <Panel>
      <PanelHeader title="Source & automation" aside={<Link href={`${base}/settings?tab=general`} className="text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">Open settings</Link>} />
      <div className="divide-y divide-border-subtle py-1">
        <Row icon={GitBranch} label="Source" value={sourceLabel(view.sourceKind)} muted={!view.sourceKind} />
        <Row icon={Package} label="Repository" value={view.repository ?? "None"} mono={!!view.repository} muted={!view.repository} />
        <Row icon={Workflow} label="CI" value={ciLabel(view.ci) ?? "Not configured"} muted={!view.ci} />
        <Row icon={Boxes} label="Services" value="No services" muted names={view.services} noun="service" />
      </div>
    </Panel>
  );
}
