"use client";

import { Check, Copy, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { Result } from "@/lib/result";
import { githubAppWebhook, hostWebhook, rotateGithubAppWebhook, rotateHostWebhook } from "./actions";

type Where = { path: string; events: string; secret: string };

const GITHUB_APP: Where = { path: "GitHub → Settings → Developer settings → GitHub Apps → the app → General → Webhook: Active, this URL as Webhook URL", events: "Then Permissions & events → Subscribe to events: Push, Pull request, Release, Workflow run, Create, Delete.", secret: "Secret" };

const WHERE: Record<string, Where> = {
  github: { path: "Repository → Settings → Webhooks → Add webhook", events: "Content type application/json. Events: Pushes, Pull requests, Releases, Workflow runs.", secret: "Secret" },
  gitlab: { path: "Project → Settings → Webhooks", events: "Triggers: Push, Tag push, Merge request, Release, Pipeline events.", secret: "Secret token" },
  bitbucket: { path: "Repository → Settings → Webhooks → Add webhook", events: "Triggers: Repository push; Pull request created, updated, merged, declined.", secret: "Secret" },
};

function Field({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(value).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => undefined); };
  return (
    <div>
      <div className="mb-1 text-xs text-secondary">{label}</div>
      <div className="flex items-center gap-1 rounded-md border border-border bg-background pl-3 pr-1">
        <span className={`min-w-0 flex-1 truncate py-2 text-[13px] ${mono ? "font-mono" : ""}`} title={value}>{value}</span>
        <Button size="icon" variant="ghost" aria-label={`Copy ${label.toLowerCase()}`} onClick={copy}>{copied ? <Check className="size-4" strokeWidth={2.5} /> : <Copy className="size-4" strokeWidth={1.75} />}</Button>
      </div>
    </div>
  );
}

export function WebhookDialog({ hostId, hostName, kind, open, onClose }: { hostId: string; hostName: string; kind: string; open: boolean; onClose: () => void }) {
  return <SecretDialog open={open} onClose={onClose} title={`Webhook for ${hostName}`} description="The host calls the platform on every push, pull request, release and pipeline; the app syncs within seconds instead of waiting for Sync." where={WHERE[kind]} load={() => hostWebhook(hostId)} rotate={() => rotateHostWebhook(hostId)} />;
}

export function GithubAppWebhookDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return <SecretDialog open={open} onClose={onClose} title="Webhook for the GitHub App" description="One webhook for every installation: each push, pull request, release and workflow run syncs the app within seconds. An App created here already has it; one created before needs it set once." where={GITHUB_APP} load={githubAppWebhook} rotate={rotateGithubAppWebhook} />;
}

function SecretDialog({ open, onClose, title, description, where, load, rotate: rotateSecret }: { open: boolean; onClose: () => void; title: string; description: string; where?: Where; load: () => Promise<Result<{ url: string; configured: boolean }>>; rotate: () => Promise<Result<{ url: string; secret: string }>> }) {
  const [info, setInfo] = useState<{ url: string; configured: boolean } | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const loader = useRef(load);
  loader.current = load;

  useEffect(() => {
    if (!open) return;
    setSecret(null);
    setError(null);
    loader.current().then((r) => { if (r.ok) setInfo(r.data); else setError(r.error); });
  }, [open]);

  const rotate = () =>
    start(async () => {
      setError(null);
      const r = await rotateSecret();
      if (r.ok) { setSecret(r.data.secret); setInfo({ url: r.data.url, configured: true }); } else setError(r.error);
    });

  return (
    <Dialog open={open} onClose={onClose} title={title} description={description} className="max-w-xl" footer={<Button onClick={onClose}>Done</Button>}>
      <div className="space-y-4 text-sm">
        {info && <Field label="Payload URL" value={info.url} />}
        {secret ? (
          <Field label={where?.secret ?? "Secret"} value={secret} />
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border-subtle px-3 py-2.5">
            <span className="text-[13px] text-secondary">{info?.configured ? "A secret is set. Generating a new one stops the old deliveries from verifying." : "No secret yet — generate one and paste it on the host."}</span>
            <Button size="sm" variant="outline" onClick={rotate} disabled={pending}><RefreshCw className={`size-3.5 ${pending ? "animate-spin" : ""}`} strokeWidth={2} /> {info?.configured ? "New secret" : "Generate secret"}</Button>
          </div>
        )}
        {secret && <p className="text-[13px] text-secondary">Shown once. Paste it as the {where?.secret ?? "secret"} on the host now.</p>}
        {where && (
          <div className="rounded-md border border-border-subtle px-3 py-2.5 text-[13px] text-secondary">
            <div><span className="text-foreground">Where:</span> {where.path}</div>
            <div className="mt-1">{where.events}</div>
          </div>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </Dialog>
  );
}
