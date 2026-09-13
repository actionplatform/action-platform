import * as Sentry from "@sentry/nextjs";
import { ApiError } from "@/lib/api";

export type Result<T = null> = { ok: true; data: T } | { ok: false; error: string };

export function failed(e: unknown, fallback = "something went wrong"): { ok: false; error: string } {
  const expected = e instanceof ApiError && e.status < 500;
  if (!expected) Sentry.captureException(e);
  const message = e instanceof Error ? e.message : String(e);
  return { ok: false, error: message || fallback };
}
