export const SENTRY_DSN = process.env.SENTRY_DSN ?? "";
export const SENTRY_ENVIRONMENT = process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV ?? "production";
export const SENTRY_TRACES_SAMPLE_RATE = Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.1");
export const WEB_VERSION = process.env.WEB_VERSION ?? "0.0.0";
export const SENTRY_RELEASE = process.env.SENTRY_RELEASE ?? `web@${WEB_VERSION}`;

export function sentryMeta(): { dsn: string; environment: string; release?: string; tracesSampleRate: number } | null {
  return SENTRY_DSN ? { dsn: SENTRY_DSN, environment: SENTRY_ENVIRONMENT, release: SENTRY_RELEASE, tracesSampleRate: SENTRY_TRACES_SAMPLE_RATE } : null;
}
