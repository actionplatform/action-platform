"use client";

import { CloudUpload } from "lucide-react";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DeployResult } from "@/lib/api";
import { previewDeploy, runDeploy } from "../actions";

export function DeployPanel({ id, hasTarget }: { id: string; hasTarget: boolean }) {
  const [stage, setStage] = useState<string>("");
  const [results, setResults] = useState<DeployResult[] | null>(null);
  const [wasDry, setWasDry] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deploy</CardTitle>
        <span className="text-xs text-muted-foreground">{hasTarget ? "preflight first, then ship" : "no [deploy] target in platform.toml"}</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <select value={stage} onChange={(e) => setStage(e.target.value)} className="h-8 rounded-md border border-border bg-card px-2 text-sm">
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
              try { setResults(await previewDeploy(id, stage || null)); setWasDry(true); } catch (e) { setError(String((e as Error).message)); }
            })}
          >
            Preflight
          </Button>
          {results && wasDry && results.every((r) => r.ok) && (
            <Button
              size="sm"
              disabled={pending}
              onClick={() => {
                if (!confirm(`Deploy ${results.map((r) => r.target).join(", ")}${stage ? ` to ${stage}` : ""}?`)) return;
                start(async () => {
                  setError(null);
                  try { setResults(await runDeploy(id, stage || null)); setWasDry(false); } catch (e) { setError(String((e as Error).message)); }
                });
              }}
            >
              <CloudUpload className="size-4" /> Deploy
            </Button>
          )}
        </div>
        {error && <div className="text-sm text-destructive">{error}</div>}
        {results && (
          <ul className="text-sm space-y-1">
            {results.map((r) => (
              <li key={r.target} className="flex items-center gap-2">
                <Badge tone={r.ok ? "ok" : "bad"}>{r.ok ? "ok" : "failed"}</Badge>
                <span className="font-mono text-xs">{r.target}</span>
                <span className="text-muted-foreground">{r.version}</span>
                {r.url && <a href={r.url} className="underline text-xs" target="_blank" rel="noreferrer">{r.url}</a>}
                {r.error && <span className="text-destructive text-xs">{r.error}</span>}
              </li>
            ))}
            <li className="text-xs text-muted-foreground">{wasDry ? "dry run" : "deployed"}</li>
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
