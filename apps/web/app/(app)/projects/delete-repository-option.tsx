"use client";

export function DeleteRepositoryOption({ id, checked, onChange, disabled, label, error }: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
  error?: string | null;
}) {
  return (
    <div className="space-y-3">
      <label htmlFor={id} className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3.5 py-3">
        <input
          id={id}
          type="checkbox"
          className="mt-0.5 size-4 shrink-0 accent-foreground"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium">{label}</span>
          <span className="block text-[13px] text-secondary">Deleted on the source host through the connected host, with every branch, tag, release and pull request. This cannot be undone.</span>
        </span>
      </label>
      {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
    </div>
  );
}
