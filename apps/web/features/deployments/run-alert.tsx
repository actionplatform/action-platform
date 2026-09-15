"use client";

import { Check, ChevronDown, CircleAlert, CircleCheck, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

export function CopyButton({ text, label = "Copy", size = "sm" }: { text: string; label?: string; size?: "sm" | "icon" }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { setDone(false); }
  };
  if (size === "icon") return <Button size="icon" variant="ghost" aria-label={label} onClick={copy}>{done ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />}</Button>;
  return <Button size="sm" variant="outline" onClick={copy}>{done ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />} {done ? "Copied" : label}</Button>;
}

export function LogBox({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("relative rounded-md border border-border-subtle bg-background", className)}>
      <div className="absolute right-1 top-1"><CopyButton text={text} label="Copy log" size="icon" /></div>
      <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words p-3 pr-10 font-mono text-xs leading-5 text-secondary">{text}</pre>
    </div>
  );
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
