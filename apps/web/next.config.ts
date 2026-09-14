import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";
import { version } from "./package.json";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: { WEB_VERSION: version },
  async rewrites() {
    const api = (process.env.AP_API ?? "http://127.0.0.1:7788").replace(/\/$/, "");
    return [
      { source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` },
      { source: "/api/auth/:path*", destination: `${api}/api/auth/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "worker-src 'self' blob:",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self' data:",
              "connect-src 'self' https://*.ingest.sentry.io https://*.ingest.us.sentry.io https://*.ingest.de.sentry.io",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self' https://github.com",
            ].join("; "),
          },
        ],
      },
    ];
  },
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
