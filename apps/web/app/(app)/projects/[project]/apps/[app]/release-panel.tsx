"use client";

import { Rocket } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import type { ReleasePreview } from "@/lib/api";
import { previewRelease, runRelease } from "../actions";

const LEVELS = ["patch", "minor", "major"];

export function ReleasePanel({ projectId, appId, registryId, branch }: { projectId: string; appId: string; registryId: string; branch: string }) {
  const [level, setLevel] = useState("patch");
  const [preview, setPreview] = useState<ReleasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [pending, start] = useTransition();
  const rc = !["main", "master"].includes(branch);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Release</CardTitle>
        <span className="text-xs text-muted-foreground">{rc ? "off main/master → rc pre-release" : "stable release"}</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <select value={level} onChange={(e) => setLevel(e.target.value)} className="h-8 rounded-md border border-border bg-background px-2 text-sm">
            {LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
          <Button
            variant="outline"
            size="sm"
            disabled={pending}
            onClick={() => start(async () => {
              setError(null);
              try { setPreview(await previewRelease(registryId, level)); } catch (e) { setError(String((e as Error).message)); }
            })}
          >
            Preview
          </Button>
          {preview && (
            <Button size="sm" disabled={pending} onClick={() => setConfirming(true)}>
              <Rocket className="size-4" /> Release {preview.next}
            </Button>
          )}
        </div>
        {preview && (
          <ConfirmDialog
            open={confirming}
            onClose={() => setConfirming(false)}
            title={`Release ${preview.next}?`}
            description={<>Tags <code className="font-mono">{preview.next}</code>, pushes it and publishes the release on the source host.{rc ? " Marked as a pre-release." : ""}</>}
            confirmLabel={`Release ${preview.next}`}
            pending={pending}
            onConfirm={() => start(async () => {
              setError(null);
              try { setPreview(await runRelease(projectId, appId, registryId, level)); setConfirming(false); } catch (e) { setError(String((e as Error).message)); setConfirming(false); }
            })}
          />
        )}
        {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
        {preview && (
          <div className="text-sm">
            <div className="text-muted-foreground mb-1">
              {preview.current} → <b className="text-foreground">{preview.next}</b>{preview.dry_run ? " (dry run)" : " — published"}
            </div>
            <pre className="max-h-48 overflow-auto rounded-md bg-background border border-border p-3 text-xs whitespace-pre-wrap">{preview.changelog || "no changes"}</pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
