import { Cpu, Hourglass, Server } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { appPath } from "@/lib/app-routes";
import { type CiAppRef, type CiHostActivity, CI_LABELS } from "@/lib/ci-kinds";
import { relativeTime } from "@/lib/time";

function Owner({ app, number }: { app: CiAppRef | null; number?: number | null }) {
  if (!app) return <span className="text-secondary">Another job on this server</span>;
  const pipelines = appPath(app.projectId, app.appId, "pipelines");
  const href = number ? `${pipelines}/${number}?${new URLSearchParams({ job: app.job }).toString()}` : `${pipelines}?${new URLSearchParams({ job: app.job }).toString()}`;
  return (
    <Link href={href} className="min-w-0 truncate hover:underline underline-offset-4">
      <span className="font-medium">{app.name}</span> <span className="font-mono text-xs text-secondary">{app.job}{number ? ` #${number}` : ""}</span>
    </Link>
  );
}

function HostPanel({ host }: { host: CiHostActivity }) {
  const busy = host.executors?.filter((e) => e.busy).length ?? 0;
  return (
    <Panel>
      <PanelHeader title={<><Server className="size-4" strokeWidth={1.75} />{host.name}<span className="font-normal text-secondary">{CI_LABELS[host.kind] ?? host.kind}</span></>} />
      {host.error ? (
        <div className="px-4 py-3 text-[13px] text-secondary">{host.error}</div>
      ) : (
        <div className="grid divide-y divide-border lg:grid-cols-2 lg:divide-x lg:divide-y-0">
          <section aria-label="Queue" className="min-w-0">
            <h3 className="flex items-center gap-2 px-4 pt-3 text-xs font-medium text-secondary"><Hourglass className="size-3.5" strokeWidth={2} /> Queue{host.queue && ` · ${host.queue.length}`}</h3>
            {host.queue === null ? (
              <p className="px-4 py-3 text-[13px] text-secondary">This CI does not report its queue.</p>
            ) : host.queue.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-secondary">Nothing waiting.</p>
            ) : (
              <ul className="divide-y divide-border-subtle">
                {host.queue.map((q, i) => (
                  <li key={i} className="space-y-0.5 px-4 py-2 text-[13px]">
                    <div className="flex min-w-0 items-center gap-2"><Owner app={q.app} />{q.since && <span className="ml-auto shrink-0 text-xs text-secondary">since {relativeTime(q.since)}</span>}</div>
                    {q.why && <p className="text-xs text-secondary">{q.why}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-label="Executors" className="min-w-0">
            <h3 className="flex items-center gap-2 px-4 pt-3 text-xs font-medium text-secondary"><Cpu className="size-3.5" strokeWidth={2} /> Executors{host.executors && ` · ${busy} of ${host.executors.length} busy`}</h3>
            {host.executors === null ? (
              <p className="px-4 py-3 text-[13px] text-secondary">This CI does not report its executors.</p>
            ) : host.executors.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-secondary">No executors.</p>
            ) : (
              <ul className="divide-y divide-border-subtle">
                {host.executors.map((e, i) => (
                  <li key={`${e.node}-${i}`} className="flex min-w-0 items-center gap-3 px-4 py-2 text-[13px]">
                    <span className={`size-2 shrink-0 rounded-full ${e.busy ? "bg-status-run" : "bg-border"}`} aria-hidden />
                    <span className="w-28 shrink-0 truncate font-mono text-xs" title={e.node}>{e.node}</span>
                    {e.busy ? <Owner app={e.app} number={e.number} /> : <span className="text-secondary">Idle</span>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </Panel>
  );
}

export function CiActivityView({ hosts }: { hosts: CiHostActivity[] }) {
  if (hosts.length === 0) {
    return <Panel><EmptyState icon={Server} title="No CI server connected" text="When the organization connects a CI server, its queue and executors show here." /></Panel>;
  }
  return <div className="space-y-4">{hosts.map((h) => <HostPanel key={h.id} host={h} />)}</div>;
}
