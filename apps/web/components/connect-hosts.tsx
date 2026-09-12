"use client";

import { Check, ExternalLink, KeyRound, Settings2, Sparkles } from "lucide-react";
import { useState, useTransition } from "react";
import { saveOAuthApp } from "@/app/oauth-actions";
import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { BrandIcon } from "@/components/ui/brand-icon";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";

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
};

export function ConnectHosts({ configured, connected, origin, orgId, returnTo, githubApp }: ConnectProps) {
  const [setup, setSetup] = useState<Provider | null>(null);
  const [createGh, setCreateGh] = useState(false);
  const [done, setDone] = useState<Record<string, boolean>>({});

  const startUrl = (p: Provider) => {
    const q = new URLSearchParams({ return: returnTo });
    if (orgId) q.set("org", orgId);
    return `/api/oauth/${p}/start?${q}`;
  };

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {(Object.keys(META) as Provider[]).map((p) => {
        const m = META[p];
        const ready = configured[p] || done[p];
        const logins = connected[p] ?? [];
        return (
          <div key={p} className="flex flex-col rounded-lg border border-border bg-surface p-4">
            <div className="flex items-center gap-2"><BrandIcon icon={m.icon} /><span className="font-medium">{m.label}</span></div>
            {logins.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-secondary">
                {logins.map((l) => <li key={l} className="flex items-center gap-1"><Check className="size-3" /> {l}</li>)}
              </ul>
            )}
            <div className="mt-auto pt-4 flex flex-col gap-2">
              {p === "github" && githubApp && (
                <a href={`https://github.com/apps/${githubApp}/installations/new`} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-foreground px-4 text-sm font-medium hover:bg-surface-hover">
                  <ExternalLink className="size-4" /> Install the app on GitHub
                </a>
              )}
              {ready ? (
                <a href={startUrl(p)} className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary-hover">
                  <KeyRound className="size-4" /> {logins.length ? "Connect another" : `Connect with ${m.label}`}
                </a>
              ) : p === "github" ? (
                <>
                  <Button onClick={() => setCreateGh(true)}><Sparkles className="size-4" /> Create GitHub App</Button>
                  <button type="button" onClick={() => setSetup(p)} className="text-xs text-muted-foreground hover:text-foreground">I already have one</button>
                </>
              ) : (
                <Button variant="outline" onClick={() => setSetup(p)}><Settings2 className="size-4" /> Set up OAuth app</Button>
              )}
              {ready && <button type="button" onClick={() => setSetup(p)} className="text-xs text-muted-foreground hover:text-foreground">Change OAuth app</button>}
            </div>
          </div>
        );
      })}

      {setup && <OAuthAppDialog provider={setup} origin={origin} onClose={() => setSetup(null)} onSaved={() => { setDone({ ...done, [setup]: true }); setSetup(null); }} />}
      {createGh && <CreateGitHubAppDialog orgId={orgId} returnTo={returnTo} onClose={() => setCreateGh(false)} />}
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
