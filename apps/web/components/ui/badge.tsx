import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

// Monochrome: "ok" and "bad" differ by weight and inversion, never by hue.
type Props = HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "ok" | "bad" | "inverse" };

export function Badge({ className, tone = "neutral", ...props }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border",
        tone === "neutral" && "border-border text-secondary",
        tone === "ok" && "border-foreground/60 text-foreground",
        tone === "bad" && "border-foreground bg-foreground text-primary-foreground",
        tone === "inverse" && "border-foreground bg-foreground text-primary-foreground",
        className,
      )}
      {...props}
    />
  );
}
