import { Check } from "lucide-react";
import { Fragment } from "react";
import { cn } from "@/lib/utils";

export const STEPS = ["Type", "Stack", "Template", "Configure", "Review"] as const;
export type StepIndex = 0 | 1 | 2 | 3 | 4;

// Active: white circle, black number. Done: white circle, black check.
// Future: dark circle, gray number. Lines follow the same rule.
export function Stepper({ current, onJump }: { current: StepIndex; onJump: (i: StepIndex) => void }) {
  return (
    <ol className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1">
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <Fragment key={label}>
            <li className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                disabled={!done}
                onClick={() => onJump(i as StepIndex)}
                className={cn(
                  "flex size-7 items-center justify-center rounded-full border text-xs font-medium transition-colors",
                  done || active ? "border-foreground bg-foreground text-primary-foreground" : "border-border bg-surface text-muted-foreground",
                  done && "cursor-pointer hover:bg-primary-hover",
                )}
                aria-current={active ? "step" : undefined}
              >
                {done ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
              </button>
              <span className={cn("text-sm", active ? "text-foreground font-medium" : done ? "text-secondary" : "text-muted-foreground")}>{label}</span>
            </li>
            {i < STEPS.length - 1 && (
              <li aria-hidden className={cn("h-px flex-1 min-w-6", i < current ? "bg-foreground" : "bg-border")} />
            )}
          </Fragment>
        );
      })}
    </ol>
  );
}
