import * as Sentry from "@sentry/nextjs";
import { ApiError } from "@/lib/api";

export type Result<T = null> = { ok: true; data: T } | { ok: false; error: string };

export const GENERIC = "Something went wrong. Try again in a moment.";
export const TIMED_OUT = "The platform took too long to answer. Try again in a moment.";

function timedOut(e: unknown): boolean {
  return (e instanceof DOMException && (e.name === "TimeoutError" || e.name === "AbortError")) || (e instanceof Error && /timeout|timed out/i.test(e.message) && !(e instanceof ApiError));
}

export function failed(e: unknown, fallback = GENERIC): { ok: false; error: string } {
  if (e instanceof ApiError && e.status < 500) return { ok: false, error: e.message || fallback };
  if (timedOut(e)) return { ok: false, error: TIMED_OUT };
  Sentry.captureException(e);
  return { ok: false, error: fallback };
}
