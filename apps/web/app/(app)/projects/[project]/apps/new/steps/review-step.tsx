"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { stackMeta, typeMeta } from "@/lib/catalog";
import { ownerOf } from "../model";
import { CommandPreview, Row, Section } from "../parts";
import type { AppWizard } from "../use-app-wizard";

export function ReviewStep({ w }: { w: AppWizard }) {
  const { config, host } = w;
  return (
    <Section title="Review your project" description="Confirm the configuration before creating the project.">
      <Card>
        <CardContent className="grid gap-x-8 gap-y-3 sm:grid-cols-2 text-sm">
          <Row k="Type" v={w.type ? typeMeta(w.matrix, w.type).label : "—"} />
          <Row k="Stack" v={w.stack ? stackMeta(w.matrix, w.stack).label : "—"} />
          <Row k="Template" v={w.template ?? "—"} mono />
          <Row k="Project name" v={config.name || "—"} />
          <Row k="Directory" v={config.directory || "—"} mono />
          <Row k="Package name" v={config.packageName || "—"} mono />
          <Row k="Description" v={config.description || "—"} />
          <Row k="Project" v={w.projects.find((p) => p.id === w.project)?.name ?? "—"} />
          <Row k="Source host" v={host?.name ?? "—"} />
          <Row k="Repository" v={host ? `${config.githubOwner || ownerOf(host) || "<token user>"}/${config.directory}` : "—"} mono />
          <div className="sm:col-span-2">
            <div className="text-xs text-secondary mb-1">Selected options</div>
            <div className="flex flex-wrap gap-1">
              {[
                config.ci && w.type !== "empty" && `CI: ${config.ciProvider}`,
                config.cloud && `Deploy: ${config.cloud}`,
                "Pushed to remote",
              ].filter(Boolean).map((o) => <Badge key={String(o)} tone="ok">{o}</Badge>)}
            </div>
          </div>
        </CardContent>
      </Card>
      <CommandPreview command={w.command} />
      {w.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{w.error}</div>}
    </Section>
  );
}
