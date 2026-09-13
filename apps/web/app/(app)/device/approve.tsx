"use client";

import { Check, ShieldCheck, X } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authClient } from "@/lib/auth-client";
import { SCOPE_INFO, SCOPES, type Scope } from "@/lib/permissions";
import { chooseDeviceScope, inspectDevice } from "./actions";

export function DeviceApprove({ initialCode }: { initialCode: string }) {
  const [code, setCode] = useState(initialCode);
  const [state, setState] = useState<"idle" | "verified" | "approved" | "denied">("idle");
  const [scope, setScope] = useState<Scope[]>([]);
  const [client, setClient] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const verify = () => start(async () => {
    setError(null);
    const r = await authClient.device({ query: { user_code: code } });
    if (r.error) return setError("invalid or expired code");
    const request = await inspectDevice(code);
    if (!request.ok) return setError(request.error);
    setScope(request.data.scope);
    setClient(request.data.clientId);
    setState("verified");
  });

  const toggle = (s: Scope) => setScope((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const decide = (approve: boolean) => start(async () => {
    setError(null);
    if (approve) {
      const chosen = await chooseDeviceScope(code, scope);
      if (!chosen.ok) return setError(chosen.error);
    }
    const r = approve ? await authClient.device.approve({ userCode: code }) : await authClient.device.deny({ userCode: code });
    if (r.error) return setError(r.error.error_description ?? "failed");
    setState(approve ? "approved" : "denied");
  });

  return (
    <Card className="max-w-md">
      <CardContent className="space-y-4">
        {state === "approved" && <div className="flex items-center gap-2 text-foreground"><ShieldCheck className="size-5" /> Approved with {scope.join(", ")}. You can close this tab; the terminal continues.</div>}
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
              <fieldset className="space-y-2">
                <legend className="text-xs text-muted-foreground">What {client ?? "the device"} may do, within your role</legend>
                {SCOPES.map((s) => {
                  const on = scope.includes(s);
                  const locked = s === "read";
                  return (
                    <label key={s} className={`flex min-h-11 cursor-pointer items-start gap-3 rounded-md border px-3 py-2 ${on ? "border-foreground" : "border-border"}`}>
                      <input type="checkbox" checked={on || locked} disabled={locked} onChange={() => toggle(s)} className="mt-1" />
                      <span className="min-w-0"><span className="block text-sm font-medium">{SCOPE_INFO[s].label}</span><span className="block text-[13px] text-secondary">{SCOPE_INFO[s].description}</span></span>
                    </label>
                  );
                })}
              </fieldset>
            )}
            {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
            {state === "idle" ? (
              <Button className="w-full" disabled={pending || code.length < 8} onClick={verify}>Continue</Button>
            ) : (
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" disabled={pending} onClick={() => decide(false)}><X className="size-4" /> Deny</Button>
                <Button className="flex-1" disabled={pending} onClick={() => decide(true)}><Check className="size-4" /> Approve</Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
