import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";
import { version } from "./package.json";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  serverExternalPackages: ["postgres", "mysql2", "@libsql/client"],
  env: { WEB_VERSION: version },
};

export default withSentryConfig(config, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
  telemetry: false,
  widenClientFileUpload: true,
  webpack: { treeshake: { removeDebugLogging: true } },
  release: { name: process.env.SENTRY_RELEASE ?? `web@${version}`, create: !!process.env.SENTRY_AUTH_TOKEN },
});
