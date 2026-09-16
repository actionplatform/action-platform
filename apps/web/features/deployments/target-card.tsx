import { Cloud, ExternalLink, Globe, Package, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Hint } from "@/components/ui/hint";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { AppView } from "@/features/projects";

function Row({ icon: Icon, label, value, mono, muted }: { icon: LucideIcon; label: string; value: string; mono?: boolean; muted?: boolean }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 text-sm">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
      <span className="w-24 shrink-0 text-secondary">{label}</span>
      <span title={value} className={`min-w-0 break-all ${mono ? "font-mono text-[13px]" : ""} ${muted ? "text-muted-foreground" : "text-foreground"}`}>{value}</span>
    </div>
  );
}

const text = (v: unknown): string | null => (typeof v === "string" && v ? v : null);

export function TargetCard({ view, base }: { view: AppView; base: string }) {
  const target = text(view.deploy.target);
  const region = text(view.deploy.region);
  const app = text(view.deploy.app) ?? `${view.orgSlug}/${view.projectSlug}/${view.name}`;
  const role = text(view.deploy.role_arn);
  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader
        title="Target"
        aside={<Link href={`${base}/configuration`} className="inline-flex items-center gap-1 text-[13px] text-secondary hover:text-foreground focus-visible:outline-none focus-visible:text-foreground">Open configuration <ExternalLink className="size-3" strokeWidth={1.75} /></Link>}
      />
      <div className="divide-y divide-border-subtle py-1">
        <Row icon={Cloud} label="Target" value={target ?? "Not configured"} mono={!!target} muted={!target} />
        <Row icon={Globe} label="Region" value={region ?? "From the target's config"} mono={!!region} muted={!region} />
        {target && <Row icon={Package} label="App" value={app} mono />}
        {role && <Row icon={Package} label="Role" value={role} mono />}
      </div>
      <div className="mt-auto flex min-h-11 w-full items-center justify-between gap-2 px-4 pb-4 pt-2 text-[13px] text-secondary">
        <span>No cloud key on the platform</span> <Hint text="Deploys run on the platform's worker with a token signed for this app; the platform stores no cloud key." />
      </div>
    </Panel>
  );
}
