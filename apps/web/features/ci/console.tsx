"use client";

import { Clock, Download, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { call } from "@/lib/call";
import { cn } from "@/lib/utils";
import { readCiLog } from "./actions";
import { type LogLine, type Segment, parseLog } from "./ansi";

const POLL_MS = 2000;
const KEEP_CHARS = 2_000_000;

type Props = { projectId: string; appId: string; job: string; number: number; node: string | null; live: boolean; downloadHref: string | null };

function styleOf(s: Segment): React.CSSProperties {
  return { color: s.fg, backgroundColor: s.bg, fontWeight: s.bold ? 600 : undefined, opacity: s.dim ? 0.7 : undefined, fontStyle: s.italic ? "italic" : undefined, textDecoration: s.underline ? "underline" : undefined };
}

function Highlighted({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>;
  const parts: React.ReactNode[] = [];
  const lower = text.toLowerCase();
  let at = 0;
  let i = lower.indexOf(query);
  while (i !== -1) {
    parts.push(text.slice(at, i), <mark key={i} className="rounded-sm bg-status-warn/40 text-foreground">{text.slice(i, i + query.length)}</mark>);
    at = i + query.length;
    i = lower.indexOf(query, at);
  }
  parts.push(text.slice(at));
  return <>{parts}</>;
}

function Line({ line, query, times }: { line: LogLine; query: string; times: boolean }) {
  return (
    <div className="flex min-w-0 gap-3 px-3 hover:bg-white/5">
      <span className="w-12 shrink-0 select-none text-right text-zinc-500">{line.number}</span>
      {times && <span className="w-[11.5rem] shrink-0 select-none text-zinc-500">{line.time ?? ""}</span>}
      <span className="min-w-0 whitespace-pre-wrap break-all">
        {query ? <Highlighted text={line.text} query={query} /> : line.segments.map((s, i) => <span key={i} style={styleOf(s)}>{s.text}</span>)}
      </span>
    </div>
  );
}

export function Console({ projectId, appId, job, number, node, live, downloadHref }: Props) {
  const [text, setText] = useState("");
  const [trimmed, setTrimmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [query, setQuery] = useState("");
  const [onlyMatches, setOnlyMatches] = useState(false);
  const [times, setTimes] = useState(false);
  const [follow, setFollow] = useState(true);
  const bottom = useRef<HTMLDivElement | null>(null);
  const following = useRef(live);

  useEffect(() => {
    following.current = live;
  }, [live]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let start = 0;
    setText("");
    setTrimmed(false);
    setError(null);
    setDone(false);

    const step = async () => {
      const r = await call(() => readCiLog(projectId, appId, job, number, start, node), (e) => ({ ok: false as const, error: e }), "Reload the page to read the log again.");
      if (cancelled) return;
      if (!r.ok) { setError(r.error); return; }
      start = r.data.nextStart;
      if (r.data.text) {
        setText((prev) => {
          const next = prev + r.data.text;
          if (next.length <= KEEP_CHARS) return next;
          setTrimmed(true);
          const cut = next.indexOf("\n", next.length - KEEP_CHARS);
          return next.slice(cut === -1 ? next.length - KEEP_CHARS : cut + 1);
        });
      }
      if (!r.data.more) { setDone(true); return; }
      timer = setTimeout(step, following.current && !r.data.truncated ? POLL_MS : 0);
    };
    step();

    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [projectId, appId, job, number, node]);

  const lines = useMemo(() => parseLog(text), [text]);
  const needle = query.trim().toLowerCase();
  const matches = useMemo(() => (needle ? lines.filter((l) => l.text.toLowerCase().includes(needle)) : lines), [lines, needle]);
  const shown = needle && onlyMatches ? matches : lines;
  const hasTimes = useMemo(() => lines.some((l) => l.time), [lines]);

  useEffect(() => {
    if (follow && !done && bottom.current) bottom.current.scrollIntoView({ block: "end" });
  }, [lines, follow, done]);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[12rem] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" strokeWidth={2} />
          <Input aria-label="Search the log" placeholder="Search the log" value={query} onChange={(e) => setQuery(e.target.value)} className="h-8 pl-8 text-[13px]" />
        </div>
        {needle && <span className="text-xs text-secondary">{matches.length} {matches.length === 1 ? "line" : "lines"}</span>}
        {needle && (
          <label className="flex items-center gap-1.5 text-xs text-secondary"><input type="checkbox" checked={onlyMatches} onChange={(e) => setOnlyMatches(e.target.checked)} /> Only matching</label>
        )}
        {hasTimes && (
          <label className="flex items-center gap-1.5 text-xs text-secondary"><input type="checkbox" checked={times} onChange={(e) => setTimes(e.target.checked)} /><Clock className="size-3.5" strokeWidth={2} /> Timestamps</label>
        )}
        {!done && live && (
          <label className="flex items-center gap-1.5 text-xs text-secondary"><input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} /> Follow</label>
        )}
        {downloadHref && (
          <a href={downloadHref} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-[13px] hover:bg-surface-hover"><Download className="size-3.5" strokeWidth={2} /> Download</a>
        )}
      </div>
      {error && <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>}
      <div role="log" aria-live={live && !done ? "polite" : "off"} className="max-h-[70vh] overflow-auto rounded-lg border border-border bg-zinc-950 py-2 font-mono text-[12px] leading-5 text-zinc-100">
        {trimmed && <div className="px-3 pb-1 text-zinc-400">Earlier lines are not kept on screen. Download the log to read all of it.</div>}
        {shown.map((l) => <Line key={l.number} line={l} query={needle} times={times && hasTimes} />)}
        {lines.length === 0 && !error && <div className="px-3 text-zinc-400">{done ? "The log is empty." : "Reading the log…"}</div>}
        {!done && lines.length > 0 && <div className={cn("px-3 text-zinc-400", live && "animate-pulse")}>{live ? "Following the run…" : "Reading…"}</div>}
        <div ref={bottom} />
      </div>
    </div>
  );
}
