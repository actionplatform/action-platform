"use client";

import { Link2, Server } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ActionField, ActionFields, ActionForm } from "@/components/ui/action-form";
import { Badge } from "@/components/ui/badge";
import { Hint } from "@/components/ui/hint";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { CI_HOST_KINDS, CI_LABELS, EMBEDDED_CI, type CiHost, type CiState } from "@/lib/ci-kinds";
import { useAction } from "@/lib/use-action";
import { RunAlert, summarize } from "@/features/deployments";
import { linkCi } from "./actions";

const EMBEDDED = "__embedded__";

type Props = { projectId: string; appId: string; state: CiState; hosts: CiHost[]; sourceKind: string | null; backHref: string };

export function ConnectCi({ projectId, appId, state, hosts, sourceKind, backHref }: Props) {
  const router = useRouter();
  const [hostId, setHostId] = useState(state.link.ciHostId ?? EMBEDDED);
  const [job, setJob] = useState(state.link.job);
  const embeddedLabel = sourceKind ? EMBEDDED_CI[sourceKind] ?? null : null;
  const host = hosts.find((h) => h.id === hostId) ?? null;
  const meta = CI_HOST_KINDS.find((k) => k.id === (host?.kind ?? "")) ?? null;
  const kind = host ? host.kind : embeddedLabel ? Object.entries(CI_LABELS).find(([, label]) => label === embeddedLabel)?.[0] ?? "none" : "none";

  const action = useAction<never, null>({
    run: () => linkCi(projectId, appId, hostId === EMBEDDED ? null : hostId, job),
    onDone: () => router.push(backHref),
  });

  const blocker = hosts.length === 0 && !embeddedLabel ? "Add a CI server under Settings first, or connect a GitHub source host." : hostId === EMBEDDED && !embeddedLabel ? "The source host has no CI of its own — pick a server." : null;

  return (
    <ActionForm
      title={state.link.kind === "none" ? "Connect CI" : "Change CI"}
      aside={<Badge className="font-mono">{CI_LABELS[state.link.kind] ?? state.link.kind}</Badge>}
      primary={{ label: "Save", icon: Link2, onClick: action.execute, disabled: !!blocker, busy: action.busy, busyLabel: "Saving…" }}
      blocker={action.error ? null : blocker}
      summary={[{ label: "Runner", value: CI_LABELS[kind] ?? kind }, { label: "Server", value: host?.baseUrl ?? (embeddedLabel ? "source host" : "—") }, { label: "Job", value: job || (kind === "github_actions" ? "all workflows" : "—") }, { label: "Credentials", value: host ? host.username ?? "token" : embeddedLabel ? "source host token" : "—" }]}
      alerts={action.error ? <RunAlert tone="danger" title="Could not save" summary={summarize(action.error)} log={action.error} /> : null}
    >
      <ActionFields>
        <ActionField label="Runner" hint={<Hint text="A CI server the organization connected under Settings, or the CI embedded in the source host — GitHub Actions reads with the host's own token." />}>
          <Select
            size="lg"
            icon={<Server className="size-4" strokeWidth={1.75} />}
            value={hostId}
            onChange={(v) => { setHostId(v); action.clearOutcome(); }}
            aria-label="Runner"
            options={[
              { value: EMBEDDED, label: embeddedLabel ?? "None", hint: embeddedLabel ? "source host token" : "no CI in the source host" },
              ...hosts.map((h) => ({ value: h.id, label: h.name, hint: `${CI_LABELS[h.kind] ?? h.kind} · ${h.baseUrl}` })),
            ]}
          />
        </ActionField>
        <ActionField label="Job" hint={<Hint text={meta?.jobHint ?? (kind === "github_actions" ? "A workflow file such as ci.yml, or empty for every workflow." : "Leave empty — one pipeline per project; a branch name filters the runs.")} />}>
          <Input className="h-[42px] rounded-[7px] font-mono" value={job} onChange={(e) => { setJob(e.target.value); action.clearOutcome(); }} placeholder={meta ? "team/app/main" : "ci.yml"} disabled={hostId === EMBEDDED && !embeddedLabel} />
        </ActionField>
      </ActionFields>
    </ActionForm>
  );
}
