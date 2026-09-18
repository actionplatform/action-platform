"use client";

import { ArrowDownToLine, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { jobLogs } from "./actions";
import { cn } from "@/lib/utils";
import { CopyButton } from "@/components/ui/copy-button";

const INTERVAL = 1500;

type Line = { seq: number; line: string };

export function useJobLog(jobId: string | null, live: boolean) {
  const [lines, setLines] = useState<Line[]>([]);
  const [finished, setFinished] = useState(!live);
  const [status, setStatus] = useState<string>("unknown");
  const next = useRef(0);
  const id = useRef<string | null>(null);

  useEffect(() => {
    if (id.current !== jobId) {
      id.current = jobId;
      next.current = 0;
      setLines([]);
      setFinished(!live);
    }
  }, [jobId, live]);

  const pull = useCallback(async () => {
    if (!jobId) return;
    const r = await jobLogs(jobId, next.current);
    if (!r.ok || id.current !== jobId) return;
    if (r.data.lines.length > 0) {
      setLines((prev) => [...prev, ...r.data.lines.map((l) => ({ seq: l.seq, line: l.line }))]);
      next.current = r.data.next;
    }
    setStatus(r.data.status);
    if (r.data.finished) setFinished(true);
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    let alive = true;
    const tick = async () => { if (alive) await pull(); };
    tick();
    if (finished && !live) return () => { alive = false; };
    const timer = setInterval(tick, INTERVAL);
    return () => { alive = false; clearInterval(timer); };
  }, [jobId, live, finished, pull]);

  return { lines, finished, status };
}

export function LiveLog({ jobId, live, title = "Run log", className, maxHeight = "max-h-72" }: { jobId: string | null; live: boolean; title?: string; className?: string; maxHeight?: string }) {
  const { lines, finished } = useJobLog(jobId, live);
  const box = useRef<HTMLPreElement>(null);
  const [follow, setFollow] = useState(true);
  const text = lines.map((l) => l.line).join("\n");
  const running = live && !finished;

  useEffect(() => {
    if (!follow || !box.current) return;
    box.current.scrollTop = box.current.scrollHeight;
  }, [lines.length, follow]);

  const onScroll = () => {
    const el = box.current;
    if (!el) return;
    setFollow(el.scrollHeight - el.scrollTop - el.clientHeight < 24);
  };

  return (
    <section className={cn("min-w-0", className)} aria-live={running ? "polite" : undefined}>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="text-xs text-secondary">{title}</span>
        {running && <Loader2 className="size-3 animate-spin text-secondary" aria-label="running" />}
        <span className="ml-auto flex items-center gap-1">
          {!follow && lines.length > 0 && <Button size="icon" variant="ghost" aria-label="Jump to the end" onClick={() => { setFollow(true); if (box.current) box.current.scrollTop = box.current.scrollHeight; }}><ArrowDownToLine className="size-3.5" strokeWidth={1.75} /></Button>}
          {text && <CopyButton text={text} label="Copy log" size="icon" />}
        </span>
      </div>
      <pre ref={box} onScroll={onScroll} tabIndex={0} className={cn("overflow-auto rounded-lg border border-border bg-background p-3 font-mono text-xs leading-5 text-secondary [overflow-wrap:anywhere] whitespace-pre-wrap focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground", maxHeight)}>
        {lines.length === 0 ? (
          <span className="text-muted-foreground">{running ? "Waiting for the worker…" : "No output recorded."}</span>
        ) : (
          lines.map((l) => <span key={l.seq} className={cn("block", l.line.startsWith("$ ") && "text-foreground")}>{l.line || " "}</span>)
        )}
      </pre>
    </section>
  );
}
