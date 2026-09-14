"use client";

import { AlertCircle, Check, ExternalLink, KeyRound, Settings2, Sparkles, UserRound, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { disconnectHost, removeOAuthApp, saveOAuthApp } from "@/app/oauth-actions";
import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Provider = "github" | "gitlab" | "bitbucket";

const META: Record<Provider, { label: string; icon: typeof siGithub; callbackHint: string; baseUrlHint: string }> = {
  github: { label: "GitHub", icon: siGithub, callbackHint: "GitHub → Settings → Developer settings → OAuth Apps → New OAuth App", baseUrlHint: "GitHub Enterprise only, e.g. https://ghe.example.com" },
  gitlab: { label: "GitLab", icon: siGitlab, callbackHint: "GitLab → Preferences → Applications (scopes: api, write_repository, read_user)", baseUrlHint: "Self-hosted only, e.g. https://gitlab.example.com" },
  bitbucket: { label: "Bitbucket", icon: siBitbucket, callbackHint: "Bitbucket → Workspace settings → OAuth consumers (account, repositories: write/admin, pull requests: write)", baseUrlHint: "" },
};

export type ConnectProps = {
  configured: Record<Provider, boolean>;
  connected: Partial<Record<Provider, string[]>>;
  origin: string;
  orgId?: string;
  returnTo: string;
  githubApp?: string | null;
  error?: string | null;
};

const DESCRIPTION: Record<Provider, string> = {
  github: "Connect repositories and manage GitHub App installations.",
  gitlab: "Connect repositories using your GitLab account.",
  bitbucket: "Connect repositories and workspaces from Bitbucket.",
};

const OAUTH_ERRORS: Record<string, string> = {
  "redirect_uri is invalid": "The OAuth redirect URI is invalid. Review the provider settings and try again.",
  "redirect_uri_mismatch": "The OAuth redirect URI does not match the one registered at the provider. Review the provider settings and try again.",
  "access_denied": "The provider reported that access was denied. Approve the request and try again.",
};

export function ConnectHosts({ configured, connected, origin, orgId, returnTo, githubApp, error: initialError }: ConnectProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [setup, setSetup] = useState<Provider | null>(null);
  const [createGh, setCreateGh] = useState(false);
  const [done, setDone] = useState<Record<string, boolean>>({});
  const [removed, setRemoved] = useState<Record<string, boolean>>({});
  const [gone, setGone] = useState<Record<string, boolean>>({});
  const [confirmRemove, setConfirmRemove] = useState<Provider | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState<{ provider: Provider; login: string } | null>(null);
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [pending, start] = useTransition();

  const installUrl = () => {
    const q = new URLSearchParams({ return: returnTo });
    if (orgId) q.set("org", orgId);
    return `/api/oauth/github/install?${q}`;
  };

  const startUrl = (p: Provider) => {
    const q = new URLSearchParams({ return: returnTo });
    if (orgId) q.set("org", orgId);
    return `/api/oauth/${p}/start?${q}`;
  };

  const dismiss = () => {
    setError(null);
    router.replace(pathname);
  };

  return (
    <div className="space-y-4">
      {error && (
        <div role="alert" className="flex flex-col gap-3 rounded-[8px] border border-[#5a2a2a] bg-[#1a0f0f] px-4 py-3 sm:flex-row sm:items-center">
          <AlertCircle className="size-5 shrink-0 text-[#e07070]" strokeWidth={1.75} aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-foreground">Connection failed</div>
            <div className="text-[13px] text-secondary">{OAUTH_ERRORS[error.trim().toLowerCase()] ?? error}</div>
          </div>
          <Button variant="outline" size="sm" className="h-9 w-full shrink-0 sm:w-auto" onClick={dismiss}>Dismiss</Button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(Object.keys(META) as Provider[]).map((p) => {
          const m = META[p];
          const ready = (configured[p] || done[p]) && !removed[p];
          const logins = (connected[p] ?? []).filter((l) => !gone[`${p}:${l}`]);
          const isConnected = ready && logins.length > 0;
          return (
            <section key={p} aria-labelledby={`host-${p}`} className="flex min-h-[280px] flex-col rounded-[8px] border border-border bg-[#111111] p-4 transition-colors hover:border-border-hover">
              <div className="flex items-center gap-2.5">
                <BrandIcon icon={m.icon} className="size-5" mono={p === "github"} />
                <h3 id={`host-${p}`} className="text-[18px] font-semibold leading-6">{m.label}</h3>
                <span className={cn("ml-auto inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 text-[12px] font-medium", isConnected ? "border-[#1f4d2b] bg-[#0f2416] text-[#6fd38a]" : "border-border text-secondary")}>
                  {isConnected && <Check className="size-3" strokeWidth={2.5} aria-hidden="true" />}
                  {isConnected ? "Connected" : "Not connected"}
                </span>
              </div>
              <p className="mt-2 text-sm leading-5 text-secondary">{DESCRIPTION[p]}</p>

              {logins.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {logins.map((l) => (
                    <li key={l} className="flex h-9 items-center gap-2 rounded-[6px] border border-border bg-background px-2.5 text-sm">
                      <UserRound className="size-4 shrink-0 text-secondary" strokeWidth={1.75} aria-hidden="true" />
                      <span className="min-w-0 flex-1 truncate">{l}</span>
                      <button type="button" aria-label={`Disconnect ${l}`} onClick={() => setConfirmDisconnect({ provider: p, login: l })} className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"><X className="size-3.5" strokeWidth={1.75} aria-hidden="true" /></button>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-auto flex flex-col gap-2 pt-4">
                {ready ? (
                  <>
                    <a href={startUrl(p)} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
                      <KeyRound className="size-4" strokeWidth={1.75} aria-hidden="true" />
                      {isConnected ? "Connect another account" : `Connect ${m.label}`}
                    </a>
                    {p === "github" && githubApp && (
                      <a href={installUrl()} title="Installs the GitHub App on another account or organization; each becomes selectable as the repository owner. If GitHub never asks where to install, the app is private — make it public under GitHub → Settings → Developer settings → GitHub Apps → Advanced." className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
                        <ExternalLink className="size-4" strokeWidth={1.75} aria-hidden="true" />
                        Install on another organization
                      </a>
                    )}
                  </>
                ) : p === "github" ? (
                  <>
                    <Button className="h-10 w-full" onClick={() => setCreateGh(true)}><Sparkles className="size-4" strokeWidth={1.75} aria-hidden="true" /> Create GitHub App</Button>
                    <Button variant="outline" className="h-10 w-full" onClick={() => setSetup(p)}><Settings2 className="size-4" strokeWidth={1.75} aria-hidden="true" /> I already have one</Button>
                  </>
                ) : (
                  <Button variant="outline" className="h-10 w-full" onClick={() => setSetup(p)}><Settings2 className="size-4" strokeWidth={1.75} aria-hidden="true" /> Set up OAuth app</Button>
                )}
                <div className="flex h-6 items-center justify-between text-[13px] text-muted-foreground">
                  {ready ? <button type="button" onClick={() => setSetup(p)} className="rounded-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">Change OAuth app</button> : <span />}
                  {isConnected && <button type="button" onClick={() => setConfirmRemove(p)} className="rounded-sm hover:text-[#e07070] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">Remove connection</button>}
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {setup && <OAuthAppDialog provider={setup} origin={origin} onClose={() => { setSetup(null); router.refresh(); }} onSaved={() => { setDone({ ...done, [setup]: true }); setSetup(null); router.refresh(); }} />}
      {createGh && <CreateGitHubAppDialog orgId={orgId} returnTo={returnTo} onClose={() => { setCreateGh(false); router.refresh(); }} />}
      <ConfirmDialog
        open={confirmRemove !== null}
        onClose={() => setConfirmRemove(null)}
        title={`Remove the ${confirmRemove ? META[confirmRemove].label : ""} connection?`}
        description="The platform forgets the OAuth app's client id and secret. Connected accounts stop refreshing their tokens; delete the app at the provider too."
        confirmLabel="Remove"
        danger
        pending={pending}
        onConfirm={() => { const p = confirmRemove; if (p) start(async () => { const r = await removeOAuthApp(p); if (r.ok) { setRemoved((m) => ({ ...m, [p]: true })); router.refresh(); } setConfirmRemove(null); }); }}
      />
      <ConfirmDialog
        open={confirmDisconnect !== null}
        onClose={() => setConfirmDisconnect(null)}
        title={`Disconnect ${confirmDisconnect?.login}?`}
        description="The stored token is deleted. Apps that used this account lose their credentials until another host is picked. Revoke the authorization at the provider too if you want it gone there."
        confirmLabel="Disconnect"
        danger
        pending={pending}
        onConfirm={() => { const c = confirmDisconnect; if (c) start(async () => { const r = await disconnectHost(c.provider, c.login); if (r.ok) { setGone((m) => ({ ...m, [`${c.provider}:${c.login}`]: true })); router.refresh(); } setConfirmDisconnect(null); }); }}
      />
    </div>
  );
}

function CreateGitHubAppDialog({ orgId, returnTo, onClose }: { orgId?: string; returnTo: string; onClose: () => void }) {
  const [org, setOrg] = useState("");
  const q = new URLSearchParams({ return: returnTo });
  if (orgId) q.set("orgId", orgId);
  if (org.trim()) q.set("org", org.trim());

  return (
    <Dialog
      open
      onClose={onClose}
      title="Create GitHub App"
      description="GitHub opens a pre-filled form; confirm the name and the app is created with the right permissions and callback. Then install it on the account or organization whose repositories the platform should manage."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <a href={`/api/oauth/github/manifest?${q}`} className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary-hover">
            <Sparkles className="size-4" /> Continue to GitHub
          </a>
        </>
      }
    >
      <Field label="GitHub organization" hint="Leave empty to create the app under your personal account.">
        <Input value={org} onChange={(e) => setOrg(e.target.value)} className="font-mono" placeholder="my-org" autoFocus />
      </Field>
    </Dialog>
  );
}

function OAuthAppDialog({ provider, origin, onClose, onSaved }: { provider: Provider; origin: string; onClose: () => void; onSaved: () => void }) {
  const m = META[provider];
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const callback = `${origin}/api/oauth/${provider}/callback`;

  return (
    <Dialog
      open
      onClose={onClose}
      title={`${m.label} OAuth app`}
      description={<>Register an OAuth app at the provider and paste its credentials. {m.callbackHint}.</>}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button
            disabled={pending || !clientId || !clientSecret}
            onClick={() => start(async () => {
              setError(null);
              const r = await saveOAuthApp({ provider, clientId, clientSecret, baseUrl });
              if (r.ok) onSaved(); else setError(r.error);
            })}
          >
            {pending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Callback URL" hint="Paste this into the OAuth app as the redirect / callback URL.">
          <Input readOnly value={callback} className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
        </Field>
        <Field label="Client ID"><Input value={clientId} onChange={(e) => setClientId(e.target.value)} className="font-mono" autoFocus /></Field>
        <Field label="Client secret" hint="Kept in the platform's config, never shown again."><Input type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} className="font-mono" /></Field>
        {m.baseUrlHint && <Field label="Base URL" hint={m.baseUrlHint}><Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="font-mono" placeholder="leave empty for the cloud service" /></Field>}
        {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
      </div>
    </Dialog>
  );
}
