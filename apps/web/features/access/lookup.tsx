"use client";

import { Search } from "lucide-react";
import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Cell } from "@/components/ui/data-table";
import { TBody, Table, Td, Th, Tr } from "@/components/ui/table";
import { SegmentedControl } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { call } from "@/lib/call";
import type { AccessWho } from "@/lib/v1";
import { lookup } from "./actions";
import { ChangeTable } from "./change-table";

type View = "person" | "service";

export function AccessLookup({ services }: { services: string[] }) {
  const [view, setView] = useState<View>("person");
  const [person, setPerson] = useState("");
  const [service, setService] = useState("");
  const [who, setWho] = useState<AccessWho | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const ready = view === "person" ? person.trim() !== "" : service !== "";

  const search = () =>
    start(async () => {
      setError(null);
      const r = await call(() => lookup(view === "person" ? { person } : { service }), (e) => ({ ok: false as const, error: e }));
      if (r.ok) setWho(r.data);
      else { setError(r.error); setWho(null); }
    });

  const grants = who?.grants ?? [];
  const drift = who?.drift ?? [];
  const accounts = Object.entries(who?.person?.accounts ?? {});

  return (
    <Panel>
      <PanelHeader title="Who has access" description="A person's accounts and live grants, or every account on a service and the member it belongs to." />
      <div className="space-y-4 p-4">
        <SegmentedControl label="Lookup" value={view} options={[{ id: "person", label: "Person" }, { id: "service", label: "Service" }]} onChange={(v) => { setView(v); setWho(null); setError(null); }} />
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); if (ready && !pending) search(); }}>
          {view === "person" ? (
            <Field label="Person (email)" className="min-w-64 flex-1"><Input type="email" value={person} onChange={(e) => setPerson(e.target.value)} placeholder="ada@example.com" autoComplete="off" /></Field>
          ) : (
            <Field label="Service" className="min-w-64 flex-1"><Select value={service} options={services.map((s) => ({ value: s, label: s }))} onChange={setService} placeholder="Choose a service" aria-label="Service" /></Field>
          )}
          <Button type="submit" variant="outline" loading={pending} disabled={!ready}><Search className="size-3.5" strokeWidth={2} /> Look up</Button>
        </form>
        {error && <div className="rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-[13px] text-status-bad">{error}</div>}
        {who && (
          <div className="space-y-4 text-[13px]">
            {who.errors && who.errors.length > 0 && (
              <ul className="space-y-1 rounded-md border border-status-bad/30 bg-status-bad/5 px-3 py-2 text-status-bad">
                {who.errors.map((e) => <li key={e} className="whitespace-pre-wrap break-words">{e}</li>)}
              </ul>
            )}
            {who.person && (
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">{who.person.name || who.person.email}</span><span className="font-mono text-secondary">{who.person.email}</span>{who.person.role && <Badge>{who.person.role}</Badge>}{!who.person.member && <Badge tone="warning">Not a member</Badge>}</div>
                {who.person.teams && who.person.teams.length > 0 && <div className="text-secondary">Teams: {who.person.teams.join(", ")}</div>}
                <div className="text-secondary">{accounts.length ? `Accounts: ${accounts.map(([s, a]) => `${s} ${a}`).join(", ")}` : "No linked accounts."}</div>
              </div>
            )}
            {grants.length > 0 ? (
              <div className="rounded-lg border border-border">
                <Table columns={[{ width: 12 }, { width: 22 }, { width: 18, hideBelow: "lg" }, { width: 22 }, { width: 12 }, { width: 14, hideBelow: "lg" }]}>
                  <thead><tr><Th>Service</Th><Th>Account</Th><Th hideBelow="lg">Member</Th><Th>Resource</Th><Th>Level</Th><Th hideBelow="lg">Why</Th></tr></thead>
                  <TBody>
                    {grants.map((g, i) => (
                      <Tr key={`${g.service}:${g.account}:${g.resource}:${i}`}>
                        <Td><Cell mono>{g.service}</Cell></Td>
                        <Td><Cell mono>{g.account}</Cell></Td>
                        <Td hideBelow="lg"><Cell title={g.person ?? "belongs to no member"}>{g.person ?? <span className="text-secondary">belongs to no member</span>}</Cell></Td>
                        <Td><Cell mono>{g.resource}</Cell></Td>
                        <Td><Cell mono>{g.level}</Cell></Td>
                        <Td hideBelow="lg"><Cell muted>{g.source ?? ""}</Cell></Td>
                      </Tr>
                    ))}
                  </TBody>
                </Table>
              </div>
            ) : (
              !who.errors?.length && <p className="text-secondary">No grants found.</p>
            )}
            {drift.length > 0 && (
              <ChangeTable title="Drift" changes={drift} pageKey="drift" />
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
