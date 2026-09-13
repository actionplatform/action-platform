import type { ReactNode } from "react";

export function PageHeader({ title, badge, description, actions }: { title: string; badge?: ReactNode; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-[26px] font-semibold leading-8">{title}</h1>
          {badge}
        </div>
        {description && <p className="mt-1.5 text-[15px] text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2 [&>a>button]:w-full [&>button]:w-full md:[&>a>button]:w-auto md:[&>button]:w-auto">{actions}</div>}
    </div>
  );
}
