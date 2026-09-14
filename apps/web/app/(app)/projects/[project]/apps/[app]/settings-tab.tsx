"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { DeleteAppDialog } from "../delete-app-dialog";
import type { AppView } from "./model";
import { PushButton } from "./push-button";

type Host = { id: string; name: string; kind: string; defaultOwner: string | null };

export function SettingsTab({ view, hosts, currentHost }: { view: AppView; hosts: Host[]; currentHost: string | null }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
      <Panel>
        <PanelHeader title="Remote repository" />
        <PanelBody className="space-y-3 text-sm">
          {view.repositoryUrl ? (
            <p className="text-secondary">Pushed to <a href={view.repositoryUrl} target="_blank" rel="noopener noreferrer" className="font-mono text-foreground hover:underline underline-offset-4">{view.repository}</a>.</p>
          ) : (
            <>
              <p className="text-secondary">This project only exists on the platform. Push it to create the repository on a code host.</p>
              {view.can["app.flow"] ? <PushButton projectId={view.projectId} appId={view.appId} registryId={view.registryId} repo={view.repository ?? view.name} hosts={hosts} current={currentHost} /> : <p className="text-[13px] text-muted-foreground">Your role cannot push repositories.</p>}
            </>
          )}
        </PanelBody>
      </Panel>

      {view.can["project.manage"] && (
        <Panel>
          <PanelHeader title="Danger zone" />
          <PanelBody className="space-y-3 text-sm">
            <p className="text-secondary">Deleting removes the platform's clone and this entry. The repository on the code host is untouched.</p>
            <Button variant="destructive" onClick={() => setConfirm(true)}>Delete project</Button>
          </PanelBody>
        </Panel>
      )}

      <DeleteAppDialog open={confirm} onClose={() => setConfirm(false)} onDeleted={() => router.push(`/projects/${view.projectId}`)} projectId={view.projectId} appId={view.appId} name={view.name} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
