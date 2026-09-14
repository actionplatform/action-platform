import { PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { type OAuthApp, readConfig } from "./config";
import { subkey } from "./keys";

export type Provider = "github" | "gitlab" | "bitbucket";

export const PROVIDERS: Record<Provider, { label: string; scopes: string; callbackHint: string }> = {
  github: { label: "GitHub", scopes: "repo workflow read:org", callbackHint: "GitHub → Settings → Developer settings → OAuth Apps" },
  gitlab: { label: "GitLab", scopes: "api write_repository read_user", callbackHint: "GitLab → User settings → Applications (or group/instance applications)" },
  bitbucket: { label: "Bitbucket", scopes: "", callbackHint: "Bitbucket → Workspace settings → OAuth consumers (permissions: account, repositories write/admin, pull requests write)" },
};

export type Token = { accessToken: string; refreshToken: string | null; expiresAt: Date | null };
export type Identity = { login: string; name: string | null };

export function appFor(provider: Provider): OAuthApp | null {
  return readConfig().oauth?.[provider] ?? null;
}

export function isConfigured(provider: Provider): boolean {
  return appFor(provider) !== null;
}

function base(provider: Provider, app: OAuthApp): string {
  if (provider === "github") return (app.baseUrl || "https://github.com").replace(/\/api\/v3$/, "").replace(/\/$/, "");
  if (provider === "gitlab") return (app.baseUrl || "https://gitlab.com").replace(/\/$/, "");
  return "https://bitbucket.org";
}

function apiBase(provider: Provider, app: OAuthApp): string {
  if (provider === "github") return app.baseUrl ? `${base(provider, app)}/api/v3` : "https://api.github.com";
  if (provider === "gitlab") return `${base(provider, app)}/api/v4`;
  return "https://api.bitbucket.org/2.0";
}

export function callbackUrl(provider: Provider, origin: string): string {
  return `${origin}/api/oauth/${provider}/callback`;
}

export function authorizeUrl(provider: Provider, origin: string, state: string): string {
  const app = appFor(provider);
  if (!app) throw new Error(`${PROVIDERS[provider].label} OAuth app is not configured`);
  const redirect = callbackUrl(provider, origin);
  const p = new URLSearchParams({ client_id: app.clientId, redirect_uri: redirect, state, response_type: "code" });
  if (PROVIDERS[provider].scopes) p.set("scope", PROVIDERS[provider].scopes);

  if (provider === "github") return `${base(provider, app)}/login/oauth/authorize?${p}`;
  if (provider === "gitlab") return `${base(provider, app)}/oauth/authorize?${p}`;
  return `https://bitbucket.org/site/oauth2/authorize?${p}`;
}

export async function exchangeCode(provider: Provider, origin: string, code: string): Promise<Token> {
  const app = appFor(provider)!;
  const redirect = callbackUrl(provider, origin);

  if (provider === "github") {
    const data = await postForm(`${base(provider, app)}/login/oauth/access_token`, { client_id: app.clientId, client_secret: app.clientSecret, code, redirect_uri: redirect });
    return token(data);
  }
  if (provider === "gitlab") {
    const data = await postForm(`${base(provider, app)}/oauth/token`, { client_id: app.clientId, client_secret: app.clientSecret, code, grant_type: "authorization_code", redirect_uri: redirect });
    return token(data);
  }
  const data = await postForm("https://bitbucket.org/site/oauth2/access_token", { grant_type: "authorization_code", code, redirect_uri: redirect }, basic(app));
  return token(data);
}

export async function refreshToken(provider: Provider, refresh: string): Promise<Token> {
  const app = appFor(provider);
  if (!app) throw new Error(`${PROVIDERS[provider].label} OAuth app is not configured`);

  if (provider === "gitlab") {
    return token(await postForm(`${base(provider, app)}/oauth/token`, { client_id: app.clientId, client_secret: app.clientSecret, refresh_token: refresh, grant_type: "refresh_token" }));
  }
  if (provider === "bitbucket") {
    return token(await postForm("https://bitbucket.org/site/oauth2/access_token", { grant_type: "refresh_token", refresh_token: refresh }, basic(app)));
  }
  return token(await postForm(`${base(provider, app)}/login/oauth/access_token`, { client_id: app.clientId, client_secret: app.clientSecret, refresh_token: refresh, grant_type: "refresh_token" }));
}

export async function identity(provider: Provider, accessToken: string): Promise<Identity> {
  const app = appFor(provider)!;
  const api = apiBase(provider, app);
  const res = await fetch(`${api}/user`, { headers: { authorization: `Bearer ${accessToken}`, accept: "application/json", "user-agent": "action-platform" }, cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`${PROVIDERS[provider].label}: could not read the signed-in user (${res.status})`);
  const u = (await res.json()) as Record<string, string>;
  const login = provider === "github" ? u.login : u.username;
  return { login, name: u.name ?? u.display_name ?? null };
}

export function apiBaseUrl(provider: Provider): string | null {
  const app = appFor(provider);
  if (!app || !app.baseUrl) return null;
  if (provider === "github") return apiBase(provider, app);
  if (provider === "gitlab") return base(provider, app);
  return null;
}

export type State = { orgId: string; returnTo: string; userId: string | null; nonce: string; ts: number };

function key(): Buffer {
  return subkey("oauth-state");
}

export function signState(state: Omit<State, "nonce" | "ts" | "userId"> & { userId?: string | null }): string {
  const payload = Buffer.from(JSON.stringify({ ...state, userId: state.userId ?? null, nonce: randomBytes(8).toString("hex"), ts: Date.now() })).toString("base64url");
  const mac = createHmac("sha256", key()).update(payload).digest("base64url");
  return `${payload}.${mac}`;
}

export function verifyState(raw: string | null, userId: string | null = null): State | null {
  if (!raw) return null;
  const [payload, mac] = raw.split(".");
  if (!payload || !mac) return null;
  const expected = createHmac("sha256", key()).update(payload).digest("base64url");
  if (expected.length !== mac.length || !timingSafeEqual(Buffer.from(expected), Buffer.from(mac))) return null;
  const state = JSON.parse(Buffer.from(payload, "base64url").toString()) as State;
  if (Date.now() - state.ts > 10 * 60_000) return null;
  if (state.userId && state.userId !== userId) return null;
  return state;
}

function basic(app: OAuthApp): Record<string, string> {
  return { authorization: `Basic ${Buffer.from(`${app.clientId}:${app.clientSecret}`).toString("base64")}` };
}

async function postForm(url: string, form: Record<string, string>, headers: Record<string, string> = {}): Promise<Record<string, unknown>> {
  const res = await fetch(url, {
    method: "POST",
    headers: { accept: "application/json", "content-type": "application/x-www-form-urlencoded", "user-agent": "action-platform", ...headers },
    body: new URLSearchParams(form),
    cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS),
  });
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok || data.error) throw new Error(String(data.error_description ?? data.error ?? `${res.status} from ${url}`));
  return data;
}

function token(data: Record<string, unknown>): Token {
  const access = data.access_token;
  if (typeof access !== "string" || !access) throw new Error("no access token in the provider's response");
  const expiresIn = typeof data.expires_in === "number" ? data.expires_in : null;
  return {
    accessToken: access,
    refreshToken: typeof data.refresh_token === "string" ? data.refresh_token : null,
    expiresAt: expiresIn ? new Date(Date.now() + expiresIn * 1000) : null,
  };
}
