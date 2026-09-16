import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({ title, badge, description, shortDescription, actions }: { title: string; badge?: ReactNode; description?: string; shortDescription?: string; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-4 md:mb-6 md:flex-row md:items-start md:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-[26px] font-semibold leading-8">{title}</h1>
          {badge}
        </div>
        {shortDescription && <p className="mt-1 line-clamp-2 text-sm text-secondary md:hidden">{shortDescription}</p>}
        {description && <p className={cn("mt-1.5 text-[15px] text-secondary", shortDescription && "hidden md:block")}>{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2 [&>a>button]:h-11 [&>a>button]:w-full [&>button]:h-11 [&>button]:w-full md:[&>a>button]:h-9 md:[&>a>button]:w-auto md:[&>button]:h-9 md:[&>button]:w-auto">{actions}</div>}
    </div>
  );
}
