"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { setAppHost } from "./actions";
import { DeleteAppDialog } from "./delete-app-dialog";
import type { AppView } from "./model";

export type HostOption = { id: string; name: string; kind: string };

export function RepositoryPanel({ view, hosts = [], currentHost = null }: { view: AppView; hosts?: HostOption[]; currentHost?: string | null }) {
  const router = useRouter();
  const [host, setHost] = useState(currentHost ?? "");
  const [saving, setSaving] = useState(false);
  const [hostError, setHostError] = useState<string | null>(null);
  const stale = !!currentHost && !hosts.some((h) => h.id === currentHost);
  const release = [view.releaseStrategy === "semver" ? "SemVer" : view.releaseStrategy, view.commitConvention === "conventional" ? "Conventional Commits" : view.commitConvention].filter(Boolean).join(" · ");

  const changeHost = async (id: string) => {
    setHost(id);
    setSaving(true);
    setHostError(null);
    const r = await setAppHost(view.projectId, view.appId, id || null);
    setSaving(false);
    if (!r.ok) setHostError(r.error);
    else router.refresh();
  };

  return (
    <Panel>
      <PanelHeader title="Repository" />
      <PanelBody className="space-y-3 text-sm">
        {view.repositoryUrl ? (
          <p className="text-secondary">Lives at <a href={view.repositoryUrl} target="_blank" rel="noopener noreferrer" className="font-mono text-foreground hover:underline underline-offset-4">{view.repository}</a>. The platform keeps no copy of its own: every action clones it fresh from there.</p>
        ) : (
          <p className="text-secondary">No remote is registered for this app.</p>
        )}
        {release && <p className="text-secondary">Releases follow <span className="text-foreground">{release}</span>.</p>}
        {view.can["app.flow"] && (
          <div className="space-y-1.5">
            <div className="text-xs text-secondary">Source host</div>
            <Select value={host} onChange={changeHost} disabled={saving} placeholder="No host — public read only" options={[{ value: "", label: "No host" }, ...hosts.map((h) => ({ value: h.id, label: h.name, hint: h.kind }))]} aria-label="Source host" />
            <p className="text-secondary">The connection whose token pushes, opens pull requests and dispatches workflows for this app.{stale ? " The one this app pointed at was removed — pick another." : ""}</p>
            {hostError && <p className="text-status-bad">{hostError}</p>}
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}

export function DangerZone({ view }: { view: AppView }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  if (!view.can["project.manage"]) return null;
  return (
    <>
      <Panel>
        <PanelHeader title="Danger zone" />
        <PanelBody className="space-y-3 text-sm">
          <p className="text-secondary">Deleting removes this app and its pending changes from the platform. The repository on the code host is untouched unless you say so.</p>
          <Button variant="destructive" onClick={() => setConfirm(true)}>Delete project</Button>
        </PanelBody>
      </Panel>
      <DeleteAppDialog open={confirm} onClose={() => setConfirm(false)} onDeleted={(queued) => router.push(queued ? `/projects/${view.projectId}/apps/${view.appId}/deployments` : `/projects/${view.projectId}`)} projectId={view.projectId} appId={view.appId} name={view.name} repositoryUrl={view.repositoryUrl} deployTarget={typeof view.deploy.target === "string" ? view.deploy.target : null} />
    </>
  );
}
