"use client";

import { Check, Cloud } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { checkAwsProxy, type ProxyHealth, saveAwsProxy } from "./actions";

export function AwsCard({ proxyUrl, orgSlug, canManage }: { proxyUrl: string | null; orgSlug: string; canManage: boolean }) {
  const [url, setUrl] = useState(proxyUrl ?? "");
  const [saved, setSaved] = useState(false);
  const [health, setHealth] = useState<ProxyHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const dirty = url.trim().replace(/\/$/, "") !== (proxyUrl ?? "");

  const check = () =>
    start(async () => {
      setError(null);
      setHealth(null);
      const r = await checkAwsProxy(url);
      if (r.ok) setHealth(r.data); else setError(r.error);
    });

  const save = () =>
    start(async () => {
      setError(null);
      const r = await saveAwsProxy(url);
      if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); } else setError(r.error);
    });

  return (
    <Card className="rounded-[11px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-6 py-5">
        <div>
          <h2 className="flex items-center gap-2 text-[15px] font-semibold"><Cloud className="size-4 text-secondary" strokeWidth={1.75} /> AWS</h2>
          <p className="mt-1 text-[13px] text-secondary">The deploy proxy in your AWS account decides which app may deploy and hands the worker short-lived credentials. No key is stored here — only the proxy&apos;s url.</p>
        </div>
      </header>
      <div className="px-6 py-5">
        <Field label="Deploy proxy url"><Input value={url} onChange={(e) => { setUrl(e.target.value); setHealth(null); }} placeholder="https://xxxx.lambda-url.us-east-1.on.aws" className="font-mono" disabled={!canManage} /></Field>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {canManage && <Button size="sm" disabled={pending || !dirty} onClick={save}>{saved ? <Check className="size-3.5" strokeWidth={2.5} /> : null} {pending && dirty ? "Saving…" : saved ? "Saved" : "Save"}</Button>}
          <Button size="sm" variant="outline" disabled={pending || !url.trim()} onClick={check}>Check</Button>
          {health && (
            <span className="text-[13px] text-secondary">
              Proxy <span className="font-mono text-foreground">{health.version}</span> for <span className="font-mono text-foreground">{health.organization}</span> in account <span className="font-mono text-foreground">{health.account}</span>
              {health.organization !== orgSlug && <> — <span className="text-foreground">serves another organization</span></>}
            </span>
          )}
        </div>
        {error && <div className="mt-3 rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        <p className="mt-4 text-[13px] text-secondary">
          Install it once with <span className="font-mono text-foreground">proxy/deploy.sh https://&lt;this platform&gt; {orgSlug}</span> from the apx-aws-lambda repository, then register each app with <span className="font-mono text-foreground">action-platform aws-lambda proxy create &lt;url&gt; {orgSlug}/&lt;project&gt;/&lt;app&gt;</span>. Apps with <span className="font-mono text-foreground">target = &quot;aws/lambda&quot;</span> deploy through it; a <span className="font-mono text-foreground">proxy_url</span> in a repository&apos;s platform.toml overrides this one.
        </p>
      </div>
    </Card>
  );
}
