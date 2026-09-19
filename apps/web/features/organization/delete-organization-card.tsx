"use client";

import { Cloud, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { TypeToConfirm } from "@/components/ui/type-to-confirm";
import { DangerIcon, DeleteRepositoryOption } from "@/features/projects";
import { deleteOrganization } from "./actions";

export function DeleteOrganizationCard({ slug, name, isOwner, projects, apps }: { slug: string; name: string; isOwner: boolean; projects: number; apps: number }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [repositories, setRepositories] = useState(false);
  const [cloud, setCloud] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const confirmed = typed.trim() === slug;

  const close = () => {
    if (pending) return;
    setOpen(false);
    setTyped("");
    setError(null);
  };

  return (
    <Panel className="border-status-bad/30">
      <PanelHeader
        title="Delete organization"
        description={`Removes ${name} from the platform with its ${projects} ${projects === 1 ? "project" : "projects"}, ${apps} ${apps === 1 ? "app" : "apps"}, members, teams, connected hosts, tokens and history. Repositories on the code host and deploy stacks stay unless you say otherwise.`}
        aside={<Button variant="destructive" size="sm" disabled={!isOwner} title={isOwner ? undefined : "Only an owner can delete the organization."} onClick={() => setOpen(true)}><Trash2 className="size-3.5" strokeWidth={1.75} /> Delete organization</Button>}
      />
      <ConfirmDialog
        open={open}
        onClose={close}
        icon={<DangerIcon />}
        title={`Delete ${name}?`}
        description="Everything the organization owns on the platform goes with it. This cannot be undone."
        confirmLabel="Delete organization"
        confirmIcon={<Trash2 className="size-4" strokeWidth={1.75} aria-hidden="true" />}
        danger
        pending={pending}
        disabled={!confirmed}
        className="rounded-[14px]"
        onConfirm={() =>
          start(async () => {
            setError(null);
            const r = await deleteOrganization(typed.trim(), repositories, cloud);
            if (!r.ok) { setError(r.error); return; }
            router.push("/projects");
            router.refresh();
          })
        }
      >
        <div className="space-y-3">
          <DeleteRepositoryOption id="delete-org-repos" checked={repositories} onChange={setRepositories} disabled={pending} label="Delete the repositories on the code hosts" detail={`${apps} ${apps === 1 ? "repository" : "repositories"}`} />
          <DeleteRepositoryOption id="delete-org-cloud" checked={cloud} onChange={setCloud} disabled={pending} label="Tear the deploy stacks down first" detail="runs on the worker; the organization leaves when every stack is gone" icon={<Cloud className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />} />
          <TypeToConfirm id="confirm-delete-org" expected={slug} value={typed} onChange={setTyped} disabled={pending} />
          {error && <div role="alert" className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
        </div>
      </ConfirmDialog>
    </Panel>
  );
}
