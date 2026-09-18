"use client";

import { Check, Copy, ExternalLink, Info } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";

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
    <Panel>
      <PanelHeader
        title={<>API <Info className="size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-label="The web app, the CLI and the MCP server talk to this API" /></>}
        description="Use the Action Platform API to integrate with your tools and automate workflows."
        aside={<Badge tone={version ? "ok" : "inverse"} className="h-6 shrink-0 px-2.5 font-mono">{version ? `v${version}` : "offline"}</Badge>}
      />
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="p-4">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Base URL</div>
          <div className="mt-2 flex gap-2">
            <div className="flex h-11 min-w-0 flex-1 items-center rounded-[8px] border border-border bg-background pl-3 pr-1 font-mono text-[13px] md:h-9">
              <span className="min-w-0 flex-1 truncate">{baseUrl}</span>
              <button type="button" aria-label={copied ? "Copied" : "Copy base URL"} onClick={copy} className="flex size-9 shrink-0 items-center justify-center rounded-md text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground md:hidden">{copied ? <Check className="size-4" strokeWidth={2.5} /> : <Copy className="size-4" strokeWidth={1.75} />}</button>
            </div>
            <Button size="sm" variant="outline" className="hidden h-9 shrink-0 md:inline-flex" onClick={copy}>{copied ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />} {copied ? "Copied" : "Copy"}</Button>
          </div>
          <p className="mt-2 text-[13px] text-secondary">Set <code className="font-mono">AP_API</code> to point the app at another host.</p>
        </div>
        <div className="flex items-center border-t border-border p-4 lg:border-l lg:border-t-0">
          <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 w-full md:h-9 md:min-h-0 items-center justify-center gap-2 rounded-[8px] border border-border px-4 text-sm transition-colors hover:border-border-hover hover:bg-surface-hover lg:w-auto">
            API documentation <ExternalLink className="size-3.5" strokeWidth={1.75} />
          </a>
        </div>
      </div>
    </Panel>
  );
}
