"use client";

import { Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/copy-button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { TBody, Table, Td, Th, Tr } from "@/components/ui/table";
import type { InstanceHealthRow } from "@/lib/v1";
import { sendTestEmail, type TestEmail } from "./actions";
import { ageText, problems } from "./health";

const REFRESH = 10000;

function Yes({ ok, yes = "Yes", no = "No" }: { ok: boolean; yes?: string; no?: string }) {
  return <Badge tone={ok ? "success" : "danger"}>{ok ? yes : no}</Badge>;
}

function TestEmailBox({ configured }: { configured: boolean }) {
  const [result, setResult] = useState<TestEmail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();

  const send = () =>
    start(async () => {
      setError(null);
      const r = await sendTestEmail();
      if (r.ok) setResult(r.data);
      else setError(r.error);
      router.refresh();
    });

  return (
    <div className="mt-3">
      <Button size="sm" variant="outline" disabled={pending || !configured} onClick={send}>
        <Mail className="size-3.5" strokeWidth={1.75} /> {pending ? "Sending…" : "Send test email"}
      </Button>
      {!configured && <span className="ml-3 text-[13px] text-secondary">Set AP_SMTP_HOST to send email.</span>}
      {result?.sent && <p className="mt-2 text-[13px]">Sent to <span className="font-mono">{result.to}</span>. Check the inbox.</p>}
      {result && !result.sent && <p className="mt-2 break-words rounded-md border border-foreground px-3 py-2 text-[13px]">{result.error}</p>}
      {error && <p className="mt-2 rounded-md border border-foreground px-3 py-2 text-[13px]">{error}</p>}
    </div>
  );
}

export function InstanceView({ health }: { health: InstanceHealthRow }) {
  const router = useRouter();
  const found = problems(health);
  const { smtp, google } = health.integrations;

  useEffect(() => {
    const timer = setInterval(() => router.refresh(), REFRESH);
    return () => clearInterval(timer);
  }, [router]);

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader title="Status" description="The same answer GET /api/health gives a monitor, refreshed every few seconds." aside={<Yes ok={health.status === "ok"} yes="Healthy" no="Needs attention" />} />
        <div className="space-y-3 p-4 text-sm">
          {found.length > 0 && (
            <ul className="space-y-1 rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-status-bad">
              {found.map((p) => <li key={p}>{p}</li>)}
            </ul>
          )}
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div><dt className="text-xs text-secondary">Database</dt><dd className="mt-0.5"><Yes ok={health.database} yes="Reachable" no="Down" /></dd></div>
            <div><dt className="text-xs text-secondary">Migrations</dt><dd className="mt-0.5"><Yes ok={health.migrations} yes="At head" no="Behind" /></dd></div>
            <div><dt className="text-xs text-secondary">Light workers</dt><dd className="mt-0.5"><Yes ok={!!health.workers.light} yes="Running" no="None" /></dd></div>
            <div><dt className="text-xs text-secondary">Deploy workers</dt><dd className="mt-0.5"><Yes ok={!!health.workers.deploy} yes="Running" no="None" /></dd></div>
          </dl>
          <p className="text-[13px] text-secondary">API {health.api} · library {health.version}</p>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Queue" description="Jobs waiting or running, per kind. A queued job with no live worker for its kind shows that in the web." />
        {health.queue.length === 0 ? (
          <p className="p-4 text-sm text-secondary">Nothing queued or running.</p>
        ) : (
          <Table>
            <thead><tr><Th>Kind</Th><Th numeric>Queued</Th><Th numeric>Running</Th><Th numeric>Oldest queued</Th><Th>Worker</Th></tr></thead>
            <TBody>
              {health.queue.map((q) => (
                <Tr key={q.kind}>
                  <Td className="font-mono text-[13px]">{q.kind}</Td>
                  <Td numeric>{q.queued}</Td>
                  <Td numeric>{q.running}</Td>
                  <Td numeric>{ageText(q.oldest_queued_seconds)}</Td>
                  <Td><Yes ok={q.worker_running} yes="Running" no="None" /></Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Workers" description="Each worker process writes a heartbeat every 15 seconds; one silent for a minute is not counted." />
        {health.workers_seen.length === 0 ? (
          <p className="p-4 text-sm text-secondary">No worker has ever started against this database.</p>
        ) : (
          <Table>
            <thead><tr><Th>Name</Th><Th>Takes</Th><Th>Last seen</Th><Th>State</Th></tr></thead>
            <TBody>
              {health.workers_seen.map((w) => (
                <Tr key={w.name}>
                  <Td className="font-mono text-[13px] [overflow-wrap:anywhere]">{w.name}</Td>
                  <Td className="font-mono text-xs [overflow-wrap:anywhere]">{w.kinds.join(", ")}</Td>
                  <Td>{new Date(w.last_seen + "Z").toLocaleTimeString()}</Td>
                  <Td><Yes ok={w.alive} yes="Alive" no="Silent" /></Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Email" description="Invitations and password resets go out over SMTP." aside={<Yes ok={smtp.configured} yes="Configured" no="Not configured" />} />
        <div className="p-4 text-sm">
          {smtp.configured && smtp.host && <p>Sending as <span className="font-mono">{smtp.sender}</span> through <span className="font-mono">{smtp.host}:{smtp.port}</span> ({smtp.security}).</p>}
          <TestEmailBox configured={smtp.configured} />
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Sign in with Google" description="Add this redirect URI to the OAuth client in the Google Cloud console." aside={<Yes ok={google.configured} yes="Configured" no="Not configured" />} />
        <div className="flex flex-wrap items-center gap-2 p-4 text-sm">
          <code className="break-all font-mono">{google.redirect_uri}</code>
          <CopyButton text={google.redirect_uri} label="Copy" />
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Integrations" />
        <dl className="grid grid-cols-1 gap-3 p-4 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-secondary">Error reporting (API)</dt><dd className="mt-0.5"><Yes ok={health.integrations.sentry_api} yes="Sentry on" no="Off" /></dd></div>
          {health.integrations.oauth_apps.map((a) => (
            <div key={a.provider}><dt className="text-xs text-secondary">{a.provider} OAuth app</dt><dd className="mt-0.5"><Yes ok={a.configured} yes="Configured" no="Not configured" /></dd></div>
          ))}
        </dl>
      </Panel>
    </div>
  );
}
