"use client";

import { ShieldCheck } from "lucide-react";
import { useState, useTransition } from "react";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { SegmentedControl } from "@/components/ui/segmented";
import { setProtectionDefault } from "./actions";

export function ProtectionDefaultCard({ initial, canManage }: { initial: boolean | null; canManage: boolean }) {
  const [enforce, setEnforce] = useState(initial);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  if (enforce === null) return null;

  const change = (next: "on" | "off") => {
    const value = next === "on";
    if (value === enforce || pending) return;
    setError(null);
    setNotice(null);
    start(async () => {
      const r = await setProtectionDefault(value);
      if (!r.ok) { setError(r.error); return; }
      setEnforce(r.data);
      setNotice(r.data ? "Saved — apps that do not say otherwise are protected; the rules are being applied in the background." : "Saved — only apps switched on in their own settings are protected.");
    });
  };

  return (
    <Panel>
      <PanelHeader title={<><ShieldCheck className="size-4 text-secondary" strokeWidth={1.75} /> Branch protection default</>} description="Whether the code host enforces git-flow for apps whose own setting is Default. New apps created here are switched on; existing apps follow this default until they say otherwise." />
      <PanelBody className="space-y-2 text-sm">
        {canManage ? (
          <SegmentedControl<"on" | "off"> label="Branch protection default" value={enforce ? "on" : "off"} onChange={change} options={[{ id: "on", label: "On" }, { id: "off", label: "Off" }]} className="max-w-xs" />
        ) : (
          <p>{enforce ? "On" : "Off"}</p>
        )}
        {pending && <p className="text-[13px] text-secondary">Saving…</p>}
        {notice && <p role="status" className="text-[13px] text-foreground">{notice}</p>}
        {error && <p role="alert" className="text-[13px] text-status-bad">{error}</p>}
      </PanelBody>
    </Panel>
  );
}
