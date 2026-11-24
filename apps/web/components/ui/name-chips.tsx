"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Hint } from "@/components/ui/hint";
import { cn } from "@/lib/utils";

type Props = { names: string[]; noun: string; max?: number; href?: string; className?: string };

export function NameChips({ names, noun, max = 2, href, className }: Props) {
  if (names.length === 0) return null;
  const shown = names.slice(0, max);
  const rest = names.length - shown.length;
  const summary = `${names.length} ${noun}${names.length === 1 ? "" : "s"}: ${names.join(", ")}`;
  const chips = (
    <>
      {shown.map((name, i) => (
        <span key={`${name}-${i}`} className="min-w-0 truncate rounded-md border border-border px-1.5 py-0.5 font-mono text-xs leading-4 text-foreground">{name}</span>
      ))}
      {rest > 0 && <Badge className="shrink-0">+{rest}</Badge>}
    </>
  );
  const inner = "flex min-w-0 max-w-full items-center gap-1.5 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-foreground";
  return (
    <Hint text={summary} className={cn("min-w-0 max-w-full", className)}>
      {href ? (
        <Link href={href} aria-label={`${summary}. Manage`} className={inner}>{chips}</Link>
      ) : (
        <span tabIndex={0} role="group" aria-label={summary} className={inner}>{chips}</span>
      )}
    </Hint>
  );
}
