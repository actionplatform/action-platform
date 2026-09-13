import * as Sentry from "@sentry/nextjs";
import type { Instrumentation } from "next";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") await import("./sentry.server.config");
  if (process.env.NEXT_RUNTIME === "edge") await import("./sentry.edge.config");
}

export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  const err = error as Error & { digest?: string; status?: number };
  console.error(
    JSON.stringify({
      level: "error",
      at: new Date().toISOString(),
      path: request.path,
      method: request.method,
      route: context.routePath,
      kind: context.routerKind,
      source: context.routeType,
      digest: err.digest,
      status: err.status,
      message: err.message,
      stack: err.stack?.split("\n").slice(0, 8).join("\n"),
    }),
  );
  Sentry.captureRequestError(error, request, context);
};
