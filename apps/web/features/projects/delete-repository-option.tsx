"use client";

import type { ReactNode } from "react";

export function DeleteRepositoryOption({
  id,
  checked,
  onChange,
  disabled,
  label,
  detail,
  icon,
  error,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
  detail?: string;
  icon?: ReactNode;
  error?: string | null;
}) {
  return (
    <div className="space-y-3">
      <label
        htmlFor={id}
        className="flex cursor-pointer items-center gap-3 rounded-md px-1 py-1 hover:bg-surface-hover"
      >
        <input
          id={id}
          type="checkbox"
          className="size-4 shrink-0 accent-foreground"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        {icon}
        <span className="min-w-0 flex-1">
          <span className="block text-sm">{label}</span>
          {detail && (
            <span className="block truncate font-mono text-xs text-secondary">
              {detail}
            </span>
          )}
        </span>
      </label>
      {error && (
        <div className="rounded-md border border-foreground px-3 py-2 text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
