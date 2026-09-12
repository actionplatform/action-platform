"use client";

import { Rocket } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReleasePreview } from "@/lib/api";
import { previewRelease, runRelease } from "../actions";

const LEVELS = ["patch", "minor", "major"];

export function ReleasePanel({ id, branch }: { id: string; branch: string }) {
  const [level, setLevel] = useState("patch");
  const [preview, setPreview] = useState<ReleasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
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
          <select value={level} onChange={(e) => setLevel(e.target.value)} className="h-8 rounded-md border border-border bg-card px-2 text-sm">
            {LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
          <Button
            variant="outline"
            size="sm"
            disabled={pending}
            onClick={() => start(async () => {
              setError(null);
              try { setPreview(await previewRelease(id, level)); } catch (e) { setError(String((e as Error).message)); }
            })}
          >
            Preview
          </Button>
          {preview && (
            <Button
              size="sm"
              disabled={pending}
              onClick={() => {
                if (!confirm(`Tag and publish ${preview.next}? This pushes and creates a release.`)) return;
                start(async () => {
                  setError(null);
                  try { setPreview(await runRelease(id, level)); } catch (e) { setError(String((e as Error).message)); }
                });
              }}
            >
              <Rocket className="size-4" /> Release {preview.next}
            </Button>
          )}
        </div>
        {error && <div className="text-sm text-destructive">{error}</div>}
        {preview && (
          <div className="text-sm">
            <div className="text-muted-foreground mb-1">
              {preview.current} → <b className="text-foreground">{preview.next}</b>{preview.dry_run ? " (dry run)" : " — published"}
            </div>
            <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">{preview.changelog || "no changes"}</pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
