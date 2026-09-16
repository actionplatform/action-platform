"use client";

import { useState, useTransition } from "react";
import { ConfirmDialog } from "@/components/ui/dialog";
import { DeleteRepositoryOption } from "./delete-repository-option";
import { removeApp } from "@/features/projects/actions";

export function DeleteAppDialog({ open, onClose, onDeleted, projectId, appId, name, repositoryUrl, deployTarget = null }: {
  open: boolean;
  onClose: () => void;
  onDeleted: (queued: boolean) => void;
  projectId: string;
  appId: string;
  name: string;
  repositoryUrl: string | null;
  deployTarget?: string | null;
}) {
  const [repository, setRepository] = useState(false);
  const [cloud, setCloud] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const host = repositoryUrl ? repositoryUrl.replace(/^https?:\/\//, "").replace(/\.git$/, "") : null;

  const close = () => {
    if (pending) return;
    setRepository(false);
    setCloud(false);
    setError(null);
    onClose();
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={close}
      title={`Delete ${name}?`}
      description={cloud ? "The deploy stacks come down first, on the worker; the app leaves the platform when that is done." : "The app and its pending changes are removed from the platform."}
      confirmLabel={cloud ? "Tear down and delete" : repository ? "Delete app and repository" : "Delete app"}
      danger
      pending={pending}
      onConfirm={() => start(async () => {
        setError(null);
        const r = await removeApp(projectId, appId, repository, cloud);
        if (r.ok) { setRepository(false); setCloud(false); onDeleted(r.job !== null); } else setError(r.error);
      })}
    >
      <div className="space-y-3">
        {host && <DeleteRepositoryOption id={`delete-repo-${appId}`} checked={repository} onChange={setRepository} disabled={pending} label={`Also delete ${host}`} />}
        {deployTarget && (
          <label htmlFor={`delete-cloud-${appId}`} className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3.5 py-3">
            <input id={`delete-cloud-${appId}`} type="checkbox" className="mt-0.5 size-4 shrink-0 accent-foreground" checked={cloud} disabled={pending} onChange={(e) => setCloud(e.target.checked)} />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">Also tear down {deployTarget}</span>
              <span className="block text-[13px] text-secondary">Every stage&apos;s stack is deleted on the cloud and the app is deregistered where it deployed. Runs on the worker; the app is removed when it finishes.</span>
            </span>
          </label>
        )}
        {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      </div>
    </ConfirmDialog>
  );
}
