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
    const api = (process.env.AP_API ?? "http://127.0.0.1:7788").replace(/\/$/, "");
    return NextResponse.rewrite(new URL(`${api}${pathname}${search}`));
  }

  if (pathname.startsWith("/api/")) return NextResponse.next();

  const headers = new Headers(request.headers);
  headers.set("x-request-path", `${pathname}${search}`);
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/((?!_next|.*\\..*).*)", "/.well-known/:path*"] };

function sameHost(source: string, host: string): boolean {
  try {
    return new URL(source).host === host;
  } catch {
    return false;
  }
}
