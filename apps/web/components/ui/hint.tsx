"use client";

import { CircleHelp } from "lucide-react";
import { type ReactNode, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

const WIDTH = 256;
const GAP = 8;

export function Hint({ text, children, className, content, pinnable = false }: { text: string; children?: ReactNode; className?: string; content?: ReactNode; pinnable?: boolean }) {
  const id = useId();
  const anchor = useRef<HTMLSpanElement>(null);
  const [hover, setHover] = useState(false);
  const [pinned, setPinned] = useState(false);
  const open = hover || pinned;
  const [box, setBox] = useState<{ top: number; left: number; above: boolean } | null>(null);

  useLayoutEffect(() => {
    if (!open || !anchor.current) { setBox(null); return; }
    const place = () => {
      const r = anchor.current!.getBoundingClientRect();
      const above = r.top > 120;
      const left = Math.min(Math.max(GAP, r.left + r.width / 2 - WIDTH / 2), window.innerWidth - WIDTH - GAP);
      setBox({ top: above ? r.top - GAP : r.bottom + GAP, left, above });
    };
    place();
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    return () => { window.removeEventListener("scroll", place, true); window.removeEventListener("resize", place); };
  }, [open]);

  useEffect(() => {
    if (!pinned) return;
    const close = (e: MouseEvent) => { if (!anchor.current?.contains(e.target as Node)) setPinned(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setPinned(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); };
  }, [pinned]);

  return (
    <span
      ref={anchor}
      className={cn("inline-flex items-center", className)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      onClick={pinnable ? () => setPinned((v) => !v) : undefined}
    >
      {children ?? <button type="button" aria-label={text} aria-describedby={open ? id : undefined} className="inline-flex text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:text-foreground"><CircleHelp className="size-3.5" strokeWidth={1.75} /></button>}
      {open && box && typeof document !== "undefined" && createPortal(
        <span
          id={id}
          role="tooltip"
          style={{ position: "fixed", top: box.top, left: box.left, width: WIDTH, transform: box.above ? "translateY(-100%)" : undefined }}
          className="pointer-events-none z-50 rounded-md border border-border bg-surface px-3 py-2 text-[12px] font-normal leading-5 text-secondary shadow-none"
        >
          {content ?? text}
        </span>,
        document.body,
      )}
    </span>
  );
}
