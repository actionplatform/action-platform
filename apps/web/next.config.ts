import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";
import { version } from "./package.json";

const dev = process.env.NODE_ENV !== "production";

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: { WEB_VERSION: version },
  async redirects() {
    return [
      { source: "/teams", destination: "/organization/teams", permanent: true },
      { source: "/teams/:team", destination: "/organization/teams/:team", permanent: true },
      { source: "/settings/members", destination: "/organization/members", permanent: true },
      { source: "/settings/people", destination: "/organization/members", permanent: true },
      { source: "/settings/people/teams", destination: "/organization/teams", permanent: true },
      { source: "/settings/people/teams/:team", destination: "/organization/teams/:team", permanent: true },
      { source: "/settings/hosts", destination: "/integrations/hosts", permanent: true },
      { source: "/settings/integrations", destination: "/integrations/hosts", permanent: true },
      { source: "/settings/gitflow", destination: "/settings", permanent: true },
      { source: "/settings/api", destination: "/organization/sessions", permanent: true },
      { source: "/settings/developers", destination: "/organization/sessions", permanent: true },
      { source: "/account", destination: "/organization/sessions", permanent: false },
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
              `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
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
