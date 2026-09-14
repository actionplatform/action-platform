"use client";

import { Check, Copy, Eye, PenLine, Rocket, Shield, ShieldCheck, Terminal, X } from "lucide-react";
import { useEffect, useState, useTransition } from "react";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { SCOPE_INFO, type Scope } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import { appChoices, approveDeviceRequest, type Choice, denyDeviceRequest, inspectDevice, type OrgChoice, projectChoices } from "./actions";

type State = "idle" | "loading" | "ready" | "approving" | "denying" | "approved" | "denied" | "expired" | "invalid" | "failed";

const ICONS: Record<Scope, typeof Eye> = { read: Eye, write: PenLine, release: Rocket, admin: ShieldCheck };
const ALL = "";
const EVERY_ORG = "*";

export function DeviceApprove({ initialCode }: { initialCode: string }) {
  const [code, setCode] = useState(initialCode);
  const [state, setState] = useState<State>(initialCode.length >= 8 ? "loading" : "idle");
  const [requested, setRequested] = useState<Scope[]>([]);
  const [granted, setGranted] = useState<Scope[]>([]);
  const [client, setClient] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [organizations, setOrganizations] = useState<OrgChoice[]>([]);
  const [projects, setProjects] = useState<Choice[]>([]);
  const [apps, setApps] = useState<Choice[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState(ALL);
  const [appId, setAppId] = useState(ALL);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pending, start] = useTransition();

  useEffect(() => {
    if (!expiresAt) return;
    const t = setInterval(() => setNow(Date.now()), 15_000);
    return () => clearInterval(t);
  }, [expiresAt]);

  const expired = state === "expired" || (expiresAt !== null && now >= expiresAt);

  useEffect(() => {
    if (expired && (state === "ready" || state === "loading")) setState("expired");
  }, [expired, state]);

  const grantableIn = (orgId: string, orgs: OrgChoice[] = organizations): Scope[] =>
    orgId === EVERY_ORG ? [...new Set(orgs.flatMap((o) => o.grantable))] : (orgs.find((o) => o.id === orgId)?.grantable ?? ["read"]);

  const loadProjects = async (orgId: string) => {
    setProjectId(ALL);
    setApps([]);
    setAppId(ALL);
    setGranted(requested.filter((s) => grantableIn(orgId).includes(s)));
    if (orgId === EVERY_ORG) { setProjects([]); return; }
    const r = await projectChoices(orgId);
    setProjects(r.ok ? r.data : []);
  };

  const loadApps = async (project: string) => {
    if (!project) { setApps([]); setAppId(ALL); return; }
    const r = await appChoices(project);
    setApps(r.ok ? r.data : []);
    setAppId(ALL);
  };

  const verify = () => start(async () => {
    setError(null);
    setState("loading");
    const request = await inspectDevice(code);
    if (!request.ok) {
      setState(request.error === "expired" ? "expired" : request.error === "invalid code" ? "invalid" : "failed");
      if (request.error !== "expired" && request.error !== "invalid code") setError(request.error);
      return;
    }
    setRequested(request.data.requested);
    setGranted(request.data.grant.scope);
    setClient(request.data.clientId);
    setExpiresAt(request.data.expiresAt);
    setNow(Date.now());
    setOrganizations(request.data.organizations);
    const orgId = request.data.grant.organizationId ?? request.data.organizations[0]?.id ?? "";
    setOrganizationId(orgId);
    if (orgId !== EVERY_ORG) {
      const p = await projectChoices(orgId);
      setProjects(p.ok ? p.data : []);
    }
    if (request.data.grant.projectId) {
      setProjectId(request.data.grant.projectId);
      const a = await appChoices(request.data.grant.projectId);
      setApps(a.ok ? a.data : []);
      if (request.data.grant.appId) setAppId(request.data.grant.appId);
    }
    setState("ready");
  });

  useEffect(() => {
    if (state === "loading" && initialCode.length >= 8) verify();
  }, []);

  const approve = () => start(async () => {
    setError(null);
    setConfirming(false);
    if (expired) { setState("expired"); return; }
    setState("approving");
    const r = await approveDeviceRequest(code, { scope: granted, organizationId, projectId: projectId || null, appId: appId || null });
    if (!r.ok) { setState(r.error === "expired" ? "expired" : "ready"); setError(r.error === "expired" ? null : r.error); return; }
    setState("approved");
  });

  const deny = () => start(async () => {
    setError(null);
    setState("denying");
    const r = await denyDeviceRequest(code);
    if (!r.ok) { setState("ready"); setError(r.error); return; }
    setState("denied");
  });

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  const kind = client && /mcp/i.test(client) ? "MCP" : "CLI";
  const clientName = client ?? "action-platform-cli";
  const everywhere = organizationId === EVERY_ORG;
  const orgName = everywhere ? "all your organizations" : organizations.find((o) => o.id === organizationId)?.name ?? "";
  const grantable = grantableIn(organizationId);
  const busy = pending || state === "approving" || state === "denying" || state === "loading";
  const minutesLeft = expiresAt ? Math.max(0, Math.ceil((expiresAt - now) / 60_000)) : null;
  const shown = requested.length ? requested : (["read"] as Scope[]);

  return (
    <div className="w-full max-w-[580px]">
      <div className="rounded-[12px] border border-border bg-surface p-5 sm:p-6">
        <div className="mb-5 flex items-center justify-center gap-2.5">
          <Logo className="size-5" />
          <span className="text-[15px] font-semibold">action-platform</span>
        </div>
        <h1 className="text-center text-[26px] font-semibold leading-tight sm:text-[32px]">Authorize a device</h1>
        <p className="mx-auto mt-2 max-w-md text-center text-[15px] leading-6 text-secondary">A CLI or MCP server is asking to act as you. Check the code matches what the terminal shows.</p>

        <div className="mt-5 flex items-center gap-2.5 rounded-[8px] border border-border bg-surface-hover px-3.5 py-3 text-[13px] text-secondary">
          <Shield className="size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />
          Only approve if you started this request.
        </div>

        {state === "approved" && <Outcome icon={<ShieldCheck className="size-5" strokeWidth={1.75} aria-hidden="true" />} title="Device approved" text={`${clientName} may now act as you with ${granted.join(", ")}${orgName ? ` on ${orgName}` : ""}. You can close this tab; the terminal continues.`} />}
        {state === "denied" && <Outcome icon={<X className="size-5" strokeWidth={1.75} aria-hidden="true" />} title="Request denied" text="The terminal was told no. Nothing was granted." />}
        {state === "expired" && <Outcome icon={<Shield className="size-5" strokeWidth={1.75} aria-hidden="true" />} title="This request expired" text="Codes last ten minutes. Run the login again in the terminal and come back with the new code." />}
        {state === "invalid" && (
          <div className="mt-5 space-y-3">
            <Outcome icon={<X className="size-5" strokeWidth={1.75} aria-hidden="true" />} title="Code not recognised" text="Check the terminal and type the code again." />
            <CodeEntry code={code} onChange={setCode} onSubmit={verify} pending={pending} />
          </div>
        )}
        {state === "failed" && (
          <div className="mt-5 space-y-3">
            <Outcome icon={<X className="size-5" strokeWidth={1.75} aria-hidden="true" />} title="Could not reach the platform" text={error ?? "Try again in a moment."} />
            <Button variant="outline" className="h-12 w-full" disabled={pending} onClick={verify}>Try again</Button>
          </div>
        )}
        {state === "idle" && <div className="mt-5"><CodeEntry code={code} onChange={setCode} onSubmit={verify} pending={pending} /></div>}
        {state === "loading" && <div className="mt-5 flex h-16 items-center justify-center text-[13px] text-secondary" role="status">Checking the code…</div>}

        {(state === "ready" || state === "approving" || state === "denying") && (
          <>
            <div className="mt-5 flex items-start gap-3 rounded-[8px] border border-border bg-background px-3.5 py-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] border border-border bg-surface"><Terminal className="size-4 text-secondary" strokeWidth={1.75} aria-hidden="true" /></div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2"><span className="truncate font-mono text-sm font-medium">{clientName}</span><span className="inline-flex h-5 items-center rounded-[5px] border border-border px-1.5 text-[11px] text-secondary">{kind}</span></div>
                <div className="text-[13px] text-secondary">Requesting access to your account</div>
              </div>
            </div>

            <div className="mt-5">
              <div className="text-xs text-secondary">Code from the terminal</div>
              <div className="relative mt-1.5 flex h-[60px] items-center justify-center rounded-[8px] border border-border bg-background">
                <span className="font-mono text-[26px] tracking-[0.3em] text-foreground" aria-label={`Authorization code ${code.split("").join(" ")}`}>{code}</span>
                <button type="button" aria-label="Copy authorization code" onClick={copy} className="absolute right-2 top-1/2 flex h-9 min-w-9 -translate-y-1/2 items-center justify-center gap-1 rounded-[6px] px-2 text-[12px] text-secondary transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
                  {copied ? <><Check className="size-4" strokeWidth={2} aria-hidden="true" /> Copied</> : <Copy className="size-4" strokeWidth={1.75} aria-hidden="true" />}
                </button>
              </div>
              <div className="mt-1.5 text-[13px] text-secondary">Confirm this code matches your terminal.</div>
            </div>

            <div className="mt-5">
              <div className="text-sm font-medium">Permissions requested</div>
              <div className="text-[13px] text-secondary">What {clientName} may do within your role{orgName ? ` in ${orgName}` : ""}.</div>
              <ul className="mt-2.5 divide-y divide-border-subtle rounded-[8px] border border-border bg-background">
                {shown.map((s) => {
                  const Icon = ICONS[s];
                  const included = granted.includes(s);
                  const blocked = !grantable.includes(s);
                  return (
                    <li key={s} className={cn("flex items-start gap-3 px-3.5 py-3", blocked && "opacity-60")}>
                      <Icon className="mt-0.5 size-4 shrink-0 text-secondary" strokeWidth={1.75} aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 text-sm font-medium">{SCOPE_INFO[s].label}{s === "admin" && <span className="inline-flex h-5 items-center rounded-[5px] border border-border px-1.5 text-[11px] font-normal text-secondary">Full access</span>}</div>
                        <div className="text-[13px] text-secondary">{blocked ? `Not available for your role in ${orgName || "this organization"}` : everywhere && organizations.some((o) => !o.grantable.includes(s)) ? `${SCOPE_INFO[s].description} — only where your role allows` : SCOPE_INFO[s].description}</div>
                      </div>
                      <span className={cn("hidden shrink-0 items-center gap-1 text-[12px] min-[400px]:inline-flex", included ? "text-foreground" : "text-muted-foreground")}>{included ? <><Check className="size-3.5" strokeWidth={2.5} aria-hidden="true" /> Included</> : "Not granted"}</span>
                      <span className="sr-only">{included ? "Included" : "Not granted"}</span>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="mt-5">
              <div className="text-sm font-medium">Where it may act</div>
              <div className="mt-2.5 grid gap-3 sm:grid-cols-2">
                <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Organization</span>
                  <Select value={organizationId} onChange={(v) => { setOrganizationId(v); void loadProjects(v); }} options={[...(organizations.length > 1 ? [{ value: EVERY_ORG, label: "All organizations", hint: "role checked per organization" }] : []), ...organizations.map((o) => ({ value: o.id, label: o.name, hint: o.role }))]} disabled={busy} />
                </label>
                {!everywhere && (
                  <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Project</span>
                    <Select value={projectId} onChange={(v) => { setProjectId(v); void loadApps(v); }} options={[{ value: ALL, label: "All projects" }, ...projects.map((p) => ({ value: p.id, label: p.name }))]} disabled={busy} />
                  </label>
                )}
                {!everywhere && projectId && (
                  <label className="block text-sm sm:col-span-2"><span className="mb-1 block text-xs text-secondary">App</span>
                    <Select value={appId} onChange={setAppId} options={[{ value: ALL, label: "All apps in the project" }, ...apps.map((a) => ({ value: a.id, label: a.name }))]} disabled={busy} />
                  </label>
                )}
              </div>
            </div>

            <div className="mt-6 border-t border-border pt-5">
              {error && <div className="mb-3 rounded-[8px] border border-foreground px-3 py-2 text-sm" role="alert">{error}</div>}
              <Button className="h-12 w-full text-[15px] font-semibold" disabled={busy || expired || !organizationId} onClick={() => setConfirming(true)}>
                <Check className="size-4" strokeWidth={2.5} aria-hidden="true" /> {state === "approving" ? "Approving…" : "Approve device"}
              </Button>
              <Button variant="outline" className="mt-2.5 h-12 w-full bg-background text-[15px]" disabled={busy} onClick={deny}>
                <X className="size-4" strokeWidth={2} aria-hidden="true" /> {state === "denying" ? "Denying…" : "Deny"}
              </Button>
              <p className="mt-3 text-center text-[12px] text-muted-foreground">{minutesLeft === null ? "This request will expire shortly." : minutesLeft <= 1 ? "This request expires in under a minute." : `This request expires in ${minutesLeft} minutes.`}</p>
            </div>
          </>
        )}
      </div>

      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={`Approve ${clientName}?`}
        description={`It will act as you with ${granted.join(", ")}${orgName ? ` on ${orgName}` : ""}${projectId ? ` — ${appId ? apps.find((a) => a.id === appId)?.name : projects.find((p) => p.id === projectId)?.name}` : ""}, for 90 days or until you revoke the token.`}
        confirmLabel="Approve device"
        pending={busy}
        onConfirm={approve}
      />
    </div>
  );
}

function Outcome({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="mt-5 flex items-start gap-3 rounded-[8px] border border-border bg-background px-3.5 py-3" role="status">
      <span className="mt-0.5 shrink-0 text-secondary">{icon}</span>
      <div><div className="text-sm font-medium">{title}</div><div className="text-[13px] text-secondary">{text}</div></div>
    </div>
  );
}

function CodeEntry({ code, onChange, onSubmit, pending }: { code: string; onChange: (v: string) => void; onSubmit: () => void; pending: boolean }) {
  return (
    <div>
      <label className="block text-sm">
        <span className="text-xs text-secondary">Code from the terminal</span>
        <input value={code} onChange={(e) => onChange(e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, ""))} onKeyDown={(e) => { if (e.key === "Enter" && code.length >= 8) onSubmit(); }} className="mt-1.5 h-[60px] w-full rounded-[8px] border border-border bg-background px-3 text-center font-mono text-[26px] tracking-[0.3em]" placeholder="ABCDEFGH" autoComplete="off" spellCheck={false} />
      </label>
      <Button className="mt-3 h-12 w-full" disabled={pending || code.length < 8} onClick={onSubmit}>Continue</Button>
    </div>
  );
}
