"use client";

import { ChevronDown, CircleAlert, CircleCheck } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CopyButton, LogBox } from "@/components/ui/copy-button";
import { cn } from "@/lib/utils";

export { CopyButton, LogBox };

export function summarize(error: string): string {
  const line = error.split("\n").map((l) => l.trim()).find((l) => l.length > 0) ?? error;
  const make = /binary: make was not successful|make: (not found|command not found)/i.test(error);
  if (make) return "Build dependency “make” could not be resolved.";
  const proxy = error.match(/proxy [A-Z]+ [^:]+: (\d{3}) ?(.*)/);
  if (proxy) return `The deploy proxy answered ${proxy[1]}${proxy[2] ? `: ${proxy[2].slice(0, 120)}` : ""}.`;
  const failed = line.match(/^(.*?) failed: (.*)$/);
  if (failed) return `${failed[1]} failed: ${failed[2].slice(0, 140)}${failed[2].length > 140 ? "…" : ""}`;
  return line.length > 160 ? `${line.slice(0, 160)}…` : line;
}

export function RunAlert({ tone, title, summary, log, defaultOpen = false }: { tone: "danger" | "success"; title: string; summary: string; log?: string | null; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = tone === "danger" ? CircleAlert : CircleCheck;
  return (
    <div className={cn("rounded-md border border-border bg-surface", tone === "danger" ? "border-l-2 border-l-status-bad" : "border-l-2 border-l-status-ok")}>
      <div className="flex flex-wrap items-center gap-3 px-3 py-2.5">
        <Icon className={cn("size-4 shrink-0", tone === "danger" ? "text-status-bad" : "text-status-ok")} strokeWidth={1.75} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">{title}</div>
          <div className="truncate text-[13px] text-secondary" title={summary}>{summary}</div>
        </div>
        {log && (
          <div className="flex items-center gap-1.5">
            <Button size="sm" variant="ghost" onClick={() => setOpen((v) => !v)} aria-expanded={open}>{open ? "Hide logs" : "View logs"}</Button>
            <CopyButton text={log} label="Copy error" />
            <Button size="icon" variant="ghost" aria-label={open ? "Collapse" : "Expand"} onClick={() => setOpen((v) => !v)}><ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} strokeWidth={1.75} /></Button>
          </div>
        )}
      </div>
      {log && open && <div className="border-t border-border-subtle p-2"><LogBox text={log} /></div>}
    </div>
  );
}
