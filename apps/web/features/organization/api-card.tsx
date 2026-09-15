"use client";

import { Check, Copy, ExternalLink, Info } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ApiCard({ baseUrl, version, docsUrl }: { baseUrl: string; version: string | null; docsUrl: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(baseUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <Card className="rounded-[11px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-6 py-5">
        <div>
          <h2 className="flex items-center gap-2 text-[15px] font-semibold">API <Info className="size-3.5 text-muted-foreground" strokeWidth={1.75} aria-label="The web app, the CLI and the MCP server talk to this API" /></h2>
          <p className="mt-1 text-[13px] text-secondary">Use the Action Platform API to integrate with your tools and automate workflows.</p>
        </div>
        <Badge tone={version ? "ok" : "inverse"} className="h-6 shrink-0 px-2.5 font-mono">{version ? `v${version}` : "offline"}</Badge>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="px-6 py-5">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Base URL</div>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <div className="flex h-9 min-w-0 flex-1 items-center rounded-[8px] border border-border bg-background px-3 font-mono text-[13px]"><span className="truncate">{baseUrl}</span></div>
            <Button size="sm" variant="outline" className="h-9 shrink-0" onClick={copy}>{copied ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />} {copied ? "Copied" : "Copy"}</Button>
          </div>
          <p className="mt-2 text-[13px] text-secondary">Set <code className="font-mono">AP_API</code> to point the app at another host.</p>
        </div>
        <div className="flex items-center border-t border-border px-6 py-5 lg:border-l lg:border-t-0">
          <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-[8px] border border-border px-4 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover lg:w-auto">
            API documentation <ExternalLink className="size-3.5" strokeWidth={1.75} />
          </a>
        </div>
      </div>
    </Card>
  );
}
