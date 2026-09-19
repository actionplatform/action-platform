import { NextResponse, type NextRequest } from "next/server";

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/api/v1/") && MUTATING.has(request.method) && !request.headers.get("authorization")) {
    const source = request.headers.get("origin") ?? request.headers.get("referer");
    const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
    if (source && host && !sameHost(source, host)) return NextResponse.json({ detail: "cross-origin request refused" }, { status: 403 });
  }

  if (pathname.startsWith("/api/v1/") || pathname.startsWith("/api/auth/") || pathname.startsWith("/.well-known/")) {
    const api = apiBase();
    return NextResponse.rewrite(new URL(`${api}${pathname}${search}`));
  }

  if (pathname.startsWith("/api/")) return NextResponse.next();

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = contentSecurityPolicy(nonce);
  const headers = new Headers(request.headers);
  headers.set("x-request-path", `${pathname}${search}`);
  headers.set("x-nonce", nonce);
  headers.set("content-security-policy", csp);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

function contentSecurityPolicy(nonce: string): string {
  const dev = process.env.NODE_ENV !== "production";
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "worker-src 'self' blob:",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://*.ingest.sentry.io https://*.ingest.us.sentry.io https://*.ingest.de.sentry.io",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self' https://github.com",
  ].join("; ");
}

export const config = { matcher: ["/((?!_next|.*\\..*).*)", "/.well-known/:path*"] };

function sameHost(source: string, host: string): boolean {
  try {
    return new URL(source).host === host;
  } catch {
    return false;
  }
}

function apiBase(): string {
  const configured = process.env.AP_API;
  if (configured) return configured.replace(/\/$/, "");
  if (process.env.NODE_ENV === "production") throw new Error("AP_API must be set: the web tier does not guess where the API is");
  return "http://127.0.0.1:7788";
}
