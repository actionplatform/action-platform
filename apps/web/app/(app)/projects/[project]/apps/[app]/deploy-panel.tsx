"use client";

import { CloudUpload } from "lucide-react";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import type { DeployResult } from "@/lib/api";
import { previewDeploy, runDeploy } from "../actions";

export function DeployPanel({ projectId, registryId, hasTarget }: { projectId: string; registryId: string; hasTarget: boolean }) {
  const [stage, setStage] = useState<string>("");
  const [results, setResults] = useState<DeployResult[] | null>(null);
  const [wasDry, setWasDry] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [pending, start] = useTransition();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deploy</CardTitle>
        <span className="text-xs text-muted-foreground">{hasTarget ? "preflight first, then ship" : "no [deploy] target in platform.toml"}</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <select value={stage} onChange={(e) => setStage(e.target.value)} className="h-8 rounded-md border border-border bg-background px-2 text-sm">
            <option value="">stage from branch</option>
            <option value="dev">dev</option>
            <option value="prod">prod</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            disabled={pending || !hasTarget}
            onClick={() => start(async () => {
              setError(null);
              try { setResults(await previewDeploy(registryId, stage || null)); setWasDry(true); } catch (e) { setError(String((e as Error).message)); }
            })}
          >
            Preflight
          </Button>
          {results && wasDry && results.every((r) => r.ok) && (
            <Button size="sm" disabled={pending} onClick={() => setConfirming(true)}>
              <CloudUpload className="size-4" /> Deploy
            </Button>
          )}
        </div>
        {results && (
          <ConfirmDialog
            open={confirming}
            onClose={() => setConfirming(false)}
            title="Deploy?"
            description={<>Ships <code className="font-mono">{results.map((r) => r.target).join(", ")}</code>{stage ? <> to <b>{stage}</b></> : " to the stage derived from the branch"}. Preflight passed.</>}
            confirmLabel="Deploy"
            pending={pending}
            onConfirm={() => start(async () => {
              setError(null);
              try { setResults(await runDeploy(projectId, registryId, stage || null)); setWasDry(false); } catch (e) { setError(String((e as Error).message)); }
              setConfirming(false);
            })}
          />
        )}
        {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
        {results && (
          <ul className="text-sm space-y-1">
            {results.map((r) => (
              <li key={r.target} className="flex items-center gap-2">
                <Badge tone={r.ok ? "ok" : "bad"}>{r.ok ? "ok" : "failed"}</Badge>
                <span className="font-mono text-xs">{r.target}</span>
                <span className="text-muted-foreground">{r.version}</span>
                {r.url && <a href={r.url} className="underline text-xs" target="_blank" rel="noreferrer">{r.url}</a>}
                {r.error && <span className="text-foreground text-xs underline decoration-dotted underline-offset-4">{r.error}</span>}
              </li>
            ))}
            <li className="text-xs text-muted-foreground">{wasDry ? "dry run" : "deployed"}</li>
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
