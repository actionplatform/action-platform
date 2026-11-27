"use client";

import { ChevronRight, FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { call } from "@/lib/call";
import type { CiTestReport } from "@/lib/ci-kinds";
import { readCiTests } from "./actions";

type Props = { projectId: string; appId: string; job: string; number: number };

export function TestsPanel({ projectId, appId, job, number }: Props) {
  const [report, setReport] = useState<CiTestReport | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    call(() => readCiTests(projectId, appId, job, number), (e) => ({ ok: false as const, error: e }), "Reload the page to read the tests again.").then((r) => {
      if (cancelled) return;
      if (r.ok) setReport(r.data);
      else setError(r.error);
    });
    return () => { cancelled = true; };
  }, [projectId, appId, job, number]);

  if (error) return <div className="rounded-md border border-border px-3 py-2 text-[13px] text-secondary">{error}</div>;
  if (report === undefined) return <Panel><div className="px-4 py-6 text-[13px] text-secondary">Reading the test report…</div></Panel>;
  if (report === null) return <Panel><EmptyState icon={FlaskConical} title="No test report" text="This run published no test results." /></Panel>;

  return (
    <Panel>
      <PanelHeader
        title="Tests"
        aside={
          <dl className="flex gap-4 text-[13px]">
            <div className="flex gap-1.5"><dt className="text-secondary">Total</dt><dd className="font-mono">{report.total}</dd></div>
            <div className="flex gap-1.5"><dt className="text-secondary">Passed</dt><dd className="font-mono text-status-ok">{report.passed}</dd></div>
            <div className="flex gap-1.5"><dt className="text-secondary">Failed</dt><dd className="font-mono text-status-bad">{report.failed}</dd></div>
            <div className="flex gap-1.5"><dt className="text-secondary">Skipped</dt><dd className="font-mono">{report.skipped}</dd></div>
          </dl>
        }
      />
      {report.failures.length === 0 ? (
        <div className="px-4 py-4 text-[13px] text-secondary">Every test passed.</div>
      ) : (
        <ul aria-label="Failed tests" className="divide-y divide-border-subtle">
          {report.failures.map((f, i) => (
            <li key={`${f.className}.${f.name}.${i}`}>
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-[13px] hover:bg-surface-hover">
                  <ChevronRight className="size-3.5 shrink-0 transition-transform group-open:rotate-90" strokeWidth={2} />
                  <span className="min-w-0 truncate font-medium" title={f.name}>{f.name}</span>
                  {f.className && <span className="min-w-0 truncate font-mono text-xs text-muted-foreground" title={f.className}>{f.className}</span>}
                </summary>
                <div className="space-y-2 px-4 pb-3 pl-10">
                  {f.message && <p className="whitespace-pre-wrap break-words text-[13px] text-status-bad">{f.message}</p>}
                  {f.stack && <pre className="max-h-80 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-[12px] leading-5">{f.stack}</pre>}
                </div>
              </details>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
