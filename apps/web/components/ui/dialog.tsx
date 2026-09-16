"use client";

import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";
import { type ReactNode, useEffect, useId, useState } from "react";
import { Button } from "./button";
import { Field, Input } from "./input";

export function Dialog({
  open,
  onClose,
  title,
  description,
  icon,
  children,
  footer,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  className?: string;
}) {
  const id = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-background/80 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal
        aria-labelledby={id}
        aria-describedby={description ? descriptionId : undefined}
        className={`max-h-[calc(100vh-2rem)] w-full max-w-md overflow-y-auto rounded-lg border border-border bg-surface ${className ?? ""}`}
      >
        <div className="flex items-start justify-between gap-4 px-4 pt-4">
          <div className="flex min-w-0 items-start gap-3">
            {icon}
            <div className="min-w-0">
              <h2 id={id} className="text-base font-semibold">
                {title}
              </h2>
              {description && (
                <div id={descriptionId} className="mt-1 text-sm text-secondary">
                  {description}
                </div>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-sm text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>
        {children && <div className="px-4 py-4">{children}</div>}
        {footer && (
          <div className="flex flex-wrap justify-end gap-2 border-t border-border px-4 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  icon,
  confirmLabel = "Confirm",
  confirmIcon,
  cancelLabel = "Cancel",
  pending,
  danger,
  disabled,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
  confirmLabel?: string;
  confirmIcon?: ReactNode;
  cancelLabel?: string;
  pending?: boolean;
  danger?: boolean;
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const formId = useId();
  const blocked = !!pending || !!disabled;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      icon={icon}
      className={className}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>
            {cancelLabel}
          </Button>
          <Button
            type="submit"
            form={formId}
            variant={
              danger ? (confirmIcon ? "danger" : "destructive") : "default"
            }
            disabled={blocked}
            aria-busy={pending || undefined}
          >
            {pending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              confirmIcon
            )}
            {pending ? "Working…" : confirmLabel}
          </Button>
        </>
      }
    >
      <form
        id={formId}
        onSubmit={(e) => {
          e.preventDefault();
          if (!blocked) onConfirm();
        }}
      >
        {children}
      </form>
    </Dialog>
  );
}

export function PromptDialog({
  open,
  onClose,
  onSubmit,
  title,
  description,
  label,
  hint,
  placeholder,
  type = "text",
  submitLabel = "Save",
  pending,
  error,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (value: string) => void;
  title: string;
  description?: ReactNode;
  label: string;
  hint?: string;
  placeholder?: string;
  type?: string;
  submitLabel?: string;
  pending?: boolean;
  error?: string | null;
}) {
  const [value, setValue] = useState("");
  useEffect(() => {
    if (open) setValue("");
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit(value)}
            disabled={pending || !value.trim()}
          >
            {pending ? "Working…" : submitLabel}
          </Button>
        </>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value);
        }}
      >
        <Field label={label} hint={hint}>
          <Input
            type={type}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            className="font-mono"
            autoFocus
          />
        </Field>
        {error && (
          <div className="mt-3 text-sm text-foreground border border-foreground rounded-md px-3 py-2">
            {error}
          </div>
        )}
      </form>
    </Dialog>
  );
}
