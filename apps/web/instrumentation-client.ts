import * as Sentry from "@sentry/nextjs";

const meta = typeof document === "undefined" ? null : document.querySelector<HTMLMetaElement>('meta[name="sentry"]')?.content;

if (meta) {
  const config = JSON.parse(meta) as { dsn: string; environment: string; release?: string; tracesSampleRate: number };
  Sentry.init({
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
