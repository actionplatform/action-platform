"use client";

import { Cloud, Trash2 } from "lucide-react";
import { useState, useTransition } from "react";
import { siBitbucket, siGithub, siGitlab } from "simple-icons";
import { BrandIcon } from "@/components/ui/brand-icon";
import { ConfirmDialog } from "@/components/ui/dialog";
import { TypeToConfirm } from "@/components/ui/type-to-confirm";
import { DeleteRepositoryOption } from "./delete-repository-option";
import { removeApp } from "@/features/projects/actions";

export function DeleteAppDialog({
  open,
  onClose,
  onDeleted,
  projectId,
  appId,
  name,
  repositoryUrl,
  deployTarget = null,
}: {
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
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const host = repositoryUrl ? hostOf(repositoryUrl) : null;
  const confirmed = typed.trim() === name;

  const reset = () => {
    setRepository(false);
    setCloud(false);
    setTyped("");
    setError(null);
  };

  const close = () => {
    if (pending) return;
    reset();
    onClose();
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={close}
      icon={<DangerIcon />}
      title={`Delete ${name}?`}
      description="This action is permanent and cannot be undone."
      confirmLabel="Delete app"
      confirmIcon={
        <Trash2 className="size-4" strokeWidth={1.75} aria-hidden="true" />
      }
      danger
      pending={pending}
      disabled={!confirmed}
      className="rounded-[14px]"
      onConfirm={() =>
        start(async () => {
          setError(null);
          const r = await removeApp(projectId, appId, repository, cloud);
          if (r.ok) {
            reset();
            onDeleted(r.job !== null);
          } else setError(r.error);
        })
      }
    >
      <div className="space-y-3">
        {host && (
          <DeleteRepositoryOption
            id={`delete-repo-${appId}`}
            checked={repository}
            onChange={setRepository}
            disabled={pending}
            label={`Delete repository on ${host.name}`}
            detail={host.repo}
            icon={
              host.icon ? (
                <BrandIcon icon={host.icon} className="size-4" mono />
              ) : undefined
            }
          />
        )}
        {deployTarget && (
          <DeleteRepositoryOption
            id={`delete-cloud-${appId}`}
            checked={cloud}
            onChange={setCloud}
            disabled={pending}
            label={`Delete stacks on ${deployTarget}`}
            icon={
              <Cloud
                className="size-4 shrink-0"
                strokeWidth={1.75}
                aria-hidden="true"
              />
            }
          />
        )}
        <TypeToConfirm
          id={`confirm-delete-${appId}`}
          expected={name}
          value={typed}
          onChange={setTyped}
          disabled={pending}
        />
        {error && (
          <div
            role="alert"
            className="rounded-md border border-foreground px-3 py-2 text-sm"
          >
            {error}
          </div>
        )}
      </div>
    </ConfirmDialog>
  );
}

export function DangerIcon() {
  return (
    <span
      className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#dc2626]/15 text-[#f87171]"
      aria-hidden="true"
    >
      <Trash2 className="size-4" strokeWidth={1.75} />
    </span>
  );
}

function hostOf(url: string): {
  name: string;
  repo: string;
  icon: typeof siGithub | null;
} {
  const path = url.replace(/^https?:\/\//, "").replace(/\.git$/, "");
  const domain = path.split("/")[0].toLowerCase();
  const repo = path.split("/").slice(1).join("/") || path;
  if (domain.includes("github"))
    return { name: "GitHub", repo, icon: siGithub };
  if (domain.includes("gitlab"))
    return { name: "GitLab", repo, icon: siGitlab };
  if (domain.includes("bitbucket"))
    return { name: "Bitbucket", repo, icon: siBitbucket };
  return { name: domain, repo, icon: null };
}
