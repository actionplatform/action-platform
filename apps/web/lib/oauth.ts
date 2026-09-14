import { type OAuthAppRow, v1 } from "./v1";

export type Provider = "github" | "gitlab" | "bitbucket";

export const PROVIDERS: Record<Provider, { label: string }> = {
  github: { label: "GitHub" },
  gitlab: { label: "GitLab" },
  bitbucket: { label: "Bitbucket" },
};

export type OAuthApp = OAuthAppRow;

export async function oauthApps(): Promise<Record<Provider, OAuthApp>> {
  const rows = await v1.oauthApps();
  return Object.fromEntries(rows.map((r) => [r.provider, r])) as Record<Provider, OAuthApp>;
}

export async function appFor(provider: Provider): Promise<OAuthApp | null> {
  const app = (await oauthApps())[provider];
  return app?.configured ? app : null;
}

export async function isConfigured(provider: Provider): Promise<boolean> {
  return (await appFor(provider)) !== null;
}
