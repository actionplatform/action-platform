"use client";

import { Check, ShieldCheck, X } from "lucide-react";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authClient } from "@/lib/auth-client";

export function DeviceApprove({ initialCode }: { initialCode: string }) {
  const [code, setCode] = useState(initialCode);
  const [state, setState] = useState<"idle" | "verified" | "approved" | "denied">("idle");
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const verify = () => start(async () => {
    setError(null);
    const r = await authClient.device({ query: { user_code: code } });
    if (r.error) return setError("invalid or expired code");
    setState("verified");
  });

  const decide = (approve: boolean) => start(async () => {
    setError(null);
    const r = approve ? await authClient.device.approve({ userCode: code }) : await authClient.device.deny({ userCode: code });
    if (r.error) return setError(r.error.error_description ?? "failed");
    setState(approve ? "approved" : "denied");
  });

  return (
    <Card className="max-w-md">
      <CardContent className="space-y-4">
        {state === "approved" && <div className="flex items-center gap-2 text-foreground"><ShieldCheck className="size-5" /> Approved. You can close this tab; the terminal continues.</div>}
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
