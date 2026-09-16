"use client";

import { Input } from "./input";

export function TypeToConfirm({
  id,
  expected,
  value,
  onChange,
  disabled,
}: {
  id: string;
  expected: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="border-t border-border pt-3">
      <label htmlFor={id} className="mb-2 block text-sm text-secondary">
        Type <span className="font-semibold text-foreground">{expected}</span>{" "}
        to confirm
      </label>
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        autoFocus
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
      />
    </div>
  );
}
