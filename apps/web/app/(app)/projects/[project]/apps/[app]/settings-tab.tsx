"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { DeleteAppDialog } from "../delete-app-dialog";
import type { AppView } from "./model";

export function SettingsTab({ view }: { view: AppView }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
      <Panel>
        <PanelHeader title="Remote repository" />
        <PanelBody className="space-y-3 text-sm">
          {view.repositoryUrl ? (
            <p className="text-secondary">Lives at <a href={view.repositoryUrl} target="_blank" rel="noopener noreferrer" className="font-mono text-foreground hover:underline underline-offset-4">{view.repository}</a>. The platform keeps no copy of its own: every action clones it fresh from there.</p>
          ) : (
            <p className="text-secondary">No remote is registered for this app.</p>
          )}
        </PanelBody>
      </Panel>

      {view.can["project.manage"] && (
        <Panel>
          <PanelHeader title="Danger zone" />
          <PanelBody className="space-y-3 text-sm">
            <p className="text-secondary">Deleting removes this app and its pending changes from the platform. The repository on the code host is untouched unless you say so.</p>
            <Button variant="destructive" onClick={() => setConfirm(true)}>Delete project</Button>
          </PanelBody>
        </Panel>
      )}

      <DeleteAppDialog open={confirm} onClose={() => setConfirm(false)} onDeleted={() => router.push(`/projects/${view.projectId}`)} projectId={view.projectId} appId={view.appId} name={view.name} repositoryUrl={view.repositoryUrl} />
    </div>
  );
}
