"use client";

import { Pause, Play, SkipForward, Square } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { type Control, controlsFor } from "./strategies";

const LABELS: Record<Control, string> = { promote: "Promote", pause: "Pause", resume: "Resume", abort: "Abort" };

export function DeploymentControls({ state, canDeploy, pending, onAct }: { state: string; canDeploy: boolean; pending?: Control | null; onAct: (control: Control) => void }) {
  const [confirming, setConfirming] = useState(false);
  const controls = controlsFor(state, canDeploy);
  if (controls.length === 0) return null;

  const icon = (c: Control) => (c === "promote" ? <SkipForward className="size-3.5" strokeWidth={1.75} /> : c === "pause" ? <Pause className="size-3.5" strokeWidth={1.75} /> : c === "resume" ? <Play className="size-3.5" strokeWidth={1.75} /> : <Square className="size-3.5" strokeWidth={1.75} />);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {controls.map((c) => (
        <Button key={c} size="sm" variant={c === "abort" ? "destructive" : "outline"} loading={pending === c} disabled={!!pending} onClick={() => (c === "abort" ? setConfirming(true) : onAct(c))}>
          {pending === c ? null : icon(c)} {LABELS[c]}
        </Button>
      ))}
      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title="Abort this deployment?"
        description="The rollout stops where it is and the platform rolls back what it already changed."
        confirmLabel="Abort deployment"
        danger
        pending={pending === "abort"}
        onConfirm={() => { setConfirming(false); onAct("abort"); }}
      />
    </div>
  );
}
