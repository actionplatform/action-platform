"use client";

import { Check, ShieldCheck, X } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { authClient } from "@/lib/auth-client";
import { SCOPE_INFO, SCOPES, type Scope } from "@/lib/permissions";
import { appChoices, type Choice, chooseDeviceGrant, inspectDevice, type OrgChoice, projectChoices } from "./actions";

const ALL = "";

export function DeviceApprove({ initialCode }: { initialCode: string }) {
  const [code, setCode] = useState(initialCode);
  const [state, setState] = useState<"idle" | "verified" | "approved" | "denied">("idle");
  const [scope, setScope] = useState<Scope[]>([]);
  const [client, setClient] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrgChoice[]>([]);
  const [projects, setProjects] = useState<Choice[]>([]);
  const [apps, setApps] = useState<Choice[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [projectId, setProjectId] = useState(ALL);
  const [appId, setAppId] = useState(ALL);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const loadProjects = async (orgId: string) => {
    const r = await projectChoices(orgId);
    setProjects(r.ok ? r.data : []);
    const allowed = organizations.find((o) => o.id === orgId)?.grantable;
    if (allowed) setScope((cur) => cur.filter((s) => allowed.includes(s)));
    setProjectId(ALL);
    setApps([]);
    setAppId(ALL);
  };

  const loadApps = async (project: string) => {
    if (!project) { setApps([]); setAppId(ALL); return; }
    const r = await appChoices(project);
    setApps(r.ok ? r.data : []);
    setAppId(ALL);
  };

  const verify = () => start(async () => {
    setError(null);
    const r = await authClient.device({ query: { user_code: code } });
    if (r.error) return setError("invalid or expired code");
    const request = await inspectDevice(code);
    if (!request.ok) return setError(request.error);
    setScope(request.data.grant.scope);
    setClient(request.data.clientId);
    setOrganizations(request.data.organizations);
    const orgId = request.data.grant.organizationId ?? request.data.organizations[0]?.id ?? "";
    setOrganizationId(orgId);
    await loadProjects(orgId);
    if (request.data.grant.projectId) { setProjectId(request.data.grant.projectId); await loadApps(request.data.grant.projectId); if (request.data.grant.appId) setAppId(request.data.grant.appId); }
    setState("verified");
  });

  const toggle = (s: Scope) => setScope((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const decide = (approve: boolean) => start(async () => {
    setError(null);
    if (approve) {
      const chosen = await chooseDeviceGrant(code, { scope, organizationId, projectId: projectId || null, appId: appId || null });
      if (!chosen.ok) return setError(chosen.error);
    }
    const r = approve ? await authClient.device.approve({ userCode: code }) : await authClient.device.deny({ userCode: code });
    if (r.error) return setError(r.error.error_description ?? "failed");
    setState(approve ? "approved" : "denied");
  });

  const currentOrg = organizations.find((o) => o.id === organizationId);
  const orgName = currentOrg?.name ?? "";
  const grantable = currentOrg?.grantable ?? ["read"];
  const reach = appId ? apps.find((a) => a.id === appId)?.name : projectId ? projects.find((p) => p.id === projectId)?.name : orgName;

  return (
    <Card className="max-w-md">
      <CardContent className="space-y-4">
        {state === "approved" && <div className="flex items-center gap-2 text-foreground"><ShieldCheck className="size-5 shrink-0" /> Approved: {scope.join(", ")} on {reach}. You can close this tab; the terminal continues.</div>}
        {state === "denied" && <div className="text-muted-foreground">Denied.</div>}
        {state !== "approved" && state !== "denied" && (
          <>
            <label className="block text-sm">
              <span className="text-muted-foreground text-xs">Code from the terminal</span>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                disabled={state === "verified"}
                className="mt-1 w-full h-11 rounded-md border border-border bg-background px-3 font-mono text-lg tracking-widest text-center"
                placeholder="ABCD-EFGH"
              />
            </label>
            {state === "verified" && (
              <>
                <fieldset className="space-y-2">
                  <legend className="text-xs text-muted-foreground">What {client ?? "the device"} may do — you are {currentOrg?.role ?? "a member"} in {orgName || "this organization"}</legend>
                  {SCOPES.map((s) => {
                    const allowed = grantable.includes(s);
                    const on = allowed && scope.includes(s);
                    const locked = s === "read";
                    return (
                      <label key={s} className={`flex min-h-11 items-start gap-3 rounded-md border px-3 py-2 ${allowed ? "cursor-pointer" : "cursor-not-allowed opacity-50"} ${on ? "border-foreground" : "border-border"}`}>
                        <input type="checkbox" checked={on || locked} disabled={locked || !allowed} onChange={() => toggle(s)} className="mt-1" />
                        <span className="min-w-0"><span className="block text-sm font-medium">{SCOPE_INFO[s].label}</span><span className="block text-[13px] text-secondary">{allowed ? SCOPE_INFO[s].description : `Your role in ${orgName} cannot grant this`}</span></span>
                      </label>
                    );
                  })}
                </fieldset>
                <fieldset className="space-y-3">
                  <legend className="text-xs text-muted-foreground">Where it may act</legend>
                  <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Organization</span>
                    <Select value={organizationId} onChange={(v) => { setOrganizationId(v); void loadProjects(v); }} options={organizations.map((o) => ({ value: o.id, label: o.name }))} />
                  </label>
                  <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Project</span>
                    <Select value={projectId} onChange={(v) => { setProjectId(v); void loadApps(v); }} options={[{ value: ALL, label: "All projects" }, ...projects.map((p) => ({ value: p.id, label: p.name }))]} />
                  </label>
                  {projectId && (
                    <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">App</span>
                      <Select value={appId} onChange={setAppId} options={[{ value: ALL, label: "All apps in the project" }, ...apps.map((a) => ({ value: a.id, label: a.name }))]} />
                    </label>
                  )}
                </fieldset>
              </>
            )}
            {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
            {state === "idle" ? (
              <Button className="w-full" disabled={pending || code.length < 8} onClick={verify}>Continue</Button>
            ) : (
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" disabled={pending} onClick={() => decide(false)}><X className="size-4" /> Deny</Button>
                <Button className="flex-1" disabled={pending || !organizationId} onClick={() => decide(true)}><Check className="size-4" /> Approve</Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
