"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { controlDeployment } from "./actions";
import { DeploymentControls } from "./deployment-controls";
import { StepTimeline } from "./step-timeline";
import { TrafficBar } from "./traffic-bar";
import { type Config, type Control, type DeploymentStep, type Safety, STATE_LABELS, STATE_TONES, configSummary, currentWeight, duration, labelOf } from "./strategies";

export type RolloutView = {
  id: string;
  target: string;
  status: string;
  strategy: string;
  strategy_config?: Config | null;
  safety?: Partial<Safety> | null;
  steps: DeploymentStep[];
};

function Item({ label, children }: { label: string; children: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-secondary">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-medium" title={children}>{children}</dd>
    </div>
  );
}

export function RolloutPanel({ projectId, appId, rollout, canDeploy }: { projectId: string; appId: string; rollout: RolloutView; canDeploy: boolean }) {
  const router = useRouter();
  const [, start] = useTransition();
  const [pending, setPending] = useState<Control | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { strategy, status, steps } = rollout;
  const summary = configSummary(strategy, rollout.strategy_config);
  const safety = rollout.safety ?? {};
  const weight = currentWeight(steps);
  const traffic = (strategy === "canary" || strategy === "blue_green") && weight !== null;

  const act = (control: Control) =>
    start(async () => {
      setPending(control);
      setError(null);
      const r = await controlDeployment(projectId, appId, rollout.id, control);
      setPending(null);
      if (!r.ok) setError(r.error);
      router.refresh();
    });

  return (
    <Panel>
      <PanelHeader
        title={<>Rollout <span className="font-mono font-normal text-secondary">{rollout.target}</span><Badge tone={STATE_TONES[status] ?? "neutral"}>{STATE_LABELS[status] ?? status}</Badge></>}
        aside={<DeploymentControls state={status} steps={steps} canDeploy={canDeploy} pending={pending} onAct={act} />}
      />
      <PanelBody className="space-y-5 text-sm">
        {error && <div role="alert" className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 min-[400px]:grid-cols-2 sm:grid-cols-4">
          <Item label="Strategy">{labelOf(strategy)}</Item>
          <Item label="Configuration">{summary.length > 0 ? summary.join(" · ") : "—"}</Item>
          <Item label="Rollback">{safety.auto_rollback === false ? "Manual" : "Automatic"}</Item>
          <Item label="Approval · bake">{`${safety.manual_approval ? "Required" : "Not required"} · ${duration(safety.bake_seconds ?? 0)}`}</Item>
        </dl>
        {traffic && <TrafficBar weight={weight} />}
        <StepTimeline steps={steps} />
      </PanelBody>
    </Panel>
  );
}
