"use client";

import { Upload } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Dialog } from "@/components/ui/dialog";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { cn } from "@/lib/utils";
import { pushApp } from "../actions";

type Host = { id: string; name: string; kind: string; defaultOwner: string | null };

export function PushButton({ projectId, appId, registryId, repo, hosts, current }: { projectId: string; appId: string; registryId: string; repo: string; hosts: Host[]; current: string | null }) {
  const [open, setOpen] = useState(false);
  const [hostId, setHostId] = useState<string>(current ?? hosts[0]?.id ?? "");
  const [priv, setPriv] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const host = hosts.find((h) => h.id === hostId);
  const target = host?.defaultOwner ? `${host.defaultOwner}/${repo.split("/").pop()}` : repo;

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}><Upload className="size-4" /> Push to remote</Button>
      <Dialog
        open={open}
        onClose={() => !pending && setOpen(false)}
        title="Push to remote"
        description={host ? <>Create <code className="font-mono">{target}</code> on {host.name} and push <code className="font-mono">main</code>.</> : "No source host configured — add one under Settings → Source hosts."}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>Cancel</Button>
            <Button
              disabled={pending || !hostId}
              onClick={() => start(async () => {
                setError(null);
                const r = await pushApp(projectId, appId, registryId, priv, hostId);
                if (r.ok) setOpen(false); else setError(r.error);
              })}
            >
              <Upload className="size-4" /> {pending ? "Pushing…" : "Push"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block text-sm">
            <span className="block text-xs text-secondary mb-1">Source host</span>
            <Select value={hostId} onChange={setHostId} disabled={hosts.length === 0} placeholder="No source host" options={hosts.map((h) => ({ value: h.id, label: h.name }))} />
          </label>
          <div>
            <div className="text-xs text-secondary mb-1">Visibility</div>
            <div className="grid grid-cols-2 gap-2">
              {[{ v: true, l: "Private", d: "Only members of the owner." }, { v: false, l: "Public", d: "Anyone can read it." }].map((o) => (
                <button key={o.l} type="button" onClick={() => setPriv(o.v)} className={cn("flex items-start gap-3 rounded-md border p-3 text-left", priv === o.v ? "border-foreground" : "border-border hover:border-border-hover")}>
                  <div className="flex-1"><div className="text-sm font-medium">{o.l}</div><div className="text-xs text-muted-foreground">{o.d}</div></div>
                  <CheckIndicator selected={priv === o.v} />
                </button>
              ))}
            </div>
          </div>
          {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2 break-words">{error}</div>}
        </div>
      </Dialog>
    </>
  );
}
