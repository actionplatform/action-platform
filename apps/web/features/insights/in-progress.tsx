"use client";

import { Cloud } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { ActiveDeployment } from "@/lib/insights";
import { elapsed } from "@/lib/time";

export const REFRESH_MS = 4000;

const COLUMNS = "@2xl:grid-cols-[minmax(0,2.2fr)_minmax(0,1.3fr)_minmax(0,1.1fr)_96px]";

function count(rows: ActiveDeployment[]): string {
  const running = rows.every((d) => d.status === "running");
  return `${rows.length} ${running ? "running" : "in progress"}`;
}

export function InProgressPanel({ deployments }: { deployments: ActiveDeployment[] }) {
  const router = useRouter();
  const [now, setNow] = useState(() => Date.now());
  const live = deployments.length > 0;

  useEffect(() => {
    if (!live) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    const refresh = setInterval(() => router.refresh(), REFRESH_MS);
    return () => { clearInterval(tick); clearInterval(refresh); };
  }, [live, router]);

  return (
    <Panel aria-labelledby="in-progress-title" className="@container rounded-[10px]">
      <PanelHeader
        className="h-14 px-5"
        title={<><span id="in-progress-title" className="text-[17px]">Deployments in progress</span>{live && <span data-testid="in-progress-count" className="text-[14px] font-normal text-secondary">{count(deployments)}</span>}</>}
      />
      {!live ? (
        <p className="px-5 py-5 text-sm text-secondary">No deployments in progress</p>
      ) : (
        <>
          <div aria-hidden className={`hidden border-b border-border px-5 py-2.5 text-[13px] font-medium text-secondary @2xl:grid @2xl:gap-4 ${COLUMNS}`}>
            <span>Deployment</span><span>Environment</span><span>Current step</span><span>Elapsed</span>
          </div>
          <ul className="divide-y divide-border-subtle">
            {deployments.map((d) => (
              <li key={d.id} data-testid="in-progress-row" className={`flex flex-col gap-2 px-5 py-3 @2xl:grid @2xl:min-h-[52px] @2xl:items-center @2xl:gap-4 @2xl:py-2 ${COLUMNS}`}>
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border text-secondary"><Cloud className="size-4" strokeWidth={1.75} aria-hidden /></span>
                  <Link href={`/projects/${d.project_id}/apps/${d.app_id}/deployments`} className="min-w-0 truncate text-[15px] font-medium hover:underline underline-offset-4">
                    {d.target}{d.version && <span className="font-mono"> {d.version}</span>}
                  </Link>
                </div>
                <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 pl-11 @2xl:contents">
                  <span className="min-w-0 truncate text-sm">{d.stage ?? "—"}</span>
                  <span><Badge tone="info" className="h-6 px-2.5 text-xs">{d.status}</Badge></span>
                  <span className="ml-auto font-mono text-sm tabular-nums @2xl:ml-0" suppressHydrationWarning>{elapsed(d.started_at, now)}</span>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
