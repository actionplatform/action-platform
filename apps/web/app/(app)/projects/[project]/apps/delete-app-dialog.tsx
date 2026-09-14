"use client";

import { useState, useTransition } from "react";
import { ConfirmDialog } from "@/components/ui/dialog";
import { DeleteRepositoryOption } from "../../delete-repository-option";
import { removeApp } from "./actions";

export function DeleteAppDialog({ open, onClose, onDeleted, projectId, appId, name, repositoryUrl }: {
  open: boolean;
  onClose: () => void;
  onDeleted: () => void;
  projectId: string;
  appId: string;
  name: string;
  repositoryUrl: string | null;
}) {
  const [repository, setRepository] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const host = repositoryUrl ? repositoryUrl.replace(/^https?:\/\//, "").replace(/\.git$/, "") : null;

  const close = () => {
    if (pending) return;
    setRepository(false);
    setError(null);
    onClose();
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={close}
      title={`Delete ${name}?`}
      description="The app and its pending changes are removed from the platform."
      confirmLabel={repository ? "Delete app and repository" : "Delete app"}
      danger
      pending={pending}
      onConfirm={() => start(async () => {
        setError(null);
        const r = await removeApp(projectId, appId, repository);
        if (r.ok) { setRepository(false); onDeleted(); } else setError(r.error);
      })}
    >
      {host && <DeleteRepositoryOption id={`delete-repo-${appId}`} checked={repository} onChange={setRepository} disabled={pending} label={`Also delete ${host}`} error={error} />}
      {!host && error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
    </ConfirmDialog>
  );
}
