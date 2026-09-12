import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Props = HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "ok" | "bad" };

export function Badge({ className, tone = "neutral", ...props }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        tone === "neutral" && "bg-muted text-muted-foreground",
        tone === "ok" && "bg-success/15 text-success",
        tone === "bad" && "bg-destructive/15 text-destructive",
        className,
      )}
      {...props}
    />
  );
}
