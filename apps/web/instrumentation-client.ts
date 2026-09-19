import * as Sentry from "@sentry/nextjs";

const meta = typeof document === "undefined" ? null : document.querySelector<HTMLMetaElement>('meta[name="sentry"]')?.content;

const DSN = /^https:\/\/[a-f0-9]+@[a-z0-9.-]+\.ingest(\.[a-z]{2})?\.sentry\.io\/[0-9]+$/i;

if (meta) {
  const config = JSON.parse(meta) as { dsn: string; environment: string; release?: string; tracesSampleRate: number };
  if (typeof config.dsn === "string" && DSN.test(config.dsn)) Sentry.init({
    dsn: config.dsn,
    environment: config.environment,
    release: config.release,
    sendDefaultPii: false,
    enableLogs: true,
    integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true })],
    tracesSampleRate: config.tracesSampleRate,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
