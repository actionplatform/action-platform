"use client";

import { Building2, Check, Database, GitBranch, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";
import { ConnectHosts } from "@/components/connect-hosts";
import { HOST_KINDS, type HostKind } from "@/lib/source-host-kinds";
import { slugify } from "@/lib/utils";
import { addSetupHost, createAdmin, createFirstOrganization, type DbForm, type HostInput, saveDatabase, testDatabase } from "./actions";

const steps = [
  { n: 1, label: "Database", icon: Database },
  { n: 2, label: "Admin", icon: UserRound },
  { n: 3, label: "Organization", icon: Building2 },
  { n: 4, label: "Source hosts", icon: GitBranch },
];

type Step = 1 | 2 | 3 | 4;

type OAuthInfo = { configured: Record<"github" | "gitlab" | "bitbucket", boolean>; origin: string; connected: string | null; error: string | null; githubApp: string | null };

export function SetupWizard({ initialStep, dbError, initialOrgId, oauth }: { initialStep: Step; dbError?: string; initialOrgId: string | null; oauth: OAuthInfo }) {
  const [step, setStep] = useState<Step>(initialStep);
  const [orgId, setOrgId] = useState<string | null>(initialOrgId);

  return (
    <Card className={cn("w-full", step === 4 ? "max-w-3xl" : "max-w-xl")}>
      <CardContent className="space-y-6">
        <div className="flex items-center gap-2 font-semibold"><Logo className="size-5" /> action-platform · setup</div>

        <ol className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {steps.map(({ n, label, icon: Icon }) => (
            <li key={n} className={cn("flex items-center gap-2", step === n ? "text-foreground" : "text-muted-foreground")}>
              <span className={cn("size-6 rounded-full border flex items-center justify-center text-xs", step >= n ? "bg-foreground text-primary-foreground border-foreground" : "border-border")}>
                {step > n ? <Check className="size-3" strokeWidth={3} /> : n}
              </span>
              <Icon className="size-4" /> {label}
            </li>
          ))}
        </ol>

        {step === 1 && <DatabaseStep onDone={() => setStep(2)} error={dbError} />}
        {step === 2 && <AdminStep onDone={() => setStep(3)} />}
        {step === 3 && <OrganizationStep onDone={(id) => { setOrgId(id); setStep(4); }} />}
        {step === 4 && <HostsStep orgId={orgId} oauth={oauth} />}
      </CardContent>
    </Card>
  );
}

const ENGINES: { id: DbForm["engine"]; label: string; port: string; user: string }[] = [
  { id: "sqlite", label: "SQLite", port: "", user: "" },
  { id: "pg", label: "PostgreSQL", port: "5432", user: "postgres" },
  { id: "mysql", label: "MySQL", port: "3306", user: "root" },
];

function DatabaseStep({ onDone, error: initialError }: { onDone: () => void; error?: string }) {
  const [form, setForm] = useState<DbForm>({ engine: "sqlite", host: "localhost", port: "", user: "", password: "", database: "action_platform", ssl: false, file: "data/app.db" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(initialError ? { ok: false, text: initialError } : null);
  const [pending, start] = useTransition();
  const set = (k: keyof DbForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const pickEngine = (id: DbForm["engine"]) => {
    const eng = ENGINES.find((e) => e.id === id)!;
    setForm({ ...form, engine: id, port: eng.port, user: eng.user });
    setMsg(null);
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => {
          const r = await saveDatabase(form);
          if (r.ok) onDone(); else setMsg({ ok: false, text: r.error });
        });
      }}
    >
      <p className="text-sm text-muted-foreground">Holds accounts and sessions. The database is created if missing, the schema migrated, and the URL saved to <code className="font-mono">config/app.json</code>.</p>
      <div className="flex gap-1 rounded-md bg-surface-hover p-1 text-sm">
        {ENGINES.map((e) => (
          <button
            key={e.id}
            type="button"
            onClick={() => pickEngine(e.id)}
            className={cn("flex-1 rounded px-3 py-1.5", form.engine === e.id ? "bg-foreground text-primary-foreground font-medium" : "text-muted-foreground hover:text-foreground")}
          >
            {e.label}
          </button>
        ))}
      </div>
      {form.engine === "sqlite" ? (
        <Field label="File"><input value={form.file} onChange={set("file")} className={cn(input, "font-mono")} required /></Field>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Host" className="col-span-2"><input value={form.host} onChange={set("host")} className={input} required /></Field>
            <Field label="Port"><input value={form.port} onChange={set("port")} className={input} required /></Field>
            <Field label="User"><input value={form.user} onChange={set("user")} className={input} required /></Field>
            <Field label="Password"><input type="password" value={form.password} onChange={set("password")} className={input} /></Field>
            <Field label="Database"><input value={form.database} onChange={set("database")} className={input} required /></Field>
          </div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.ssl} onChange={set("ssl")} /> require SSL</label>
        </>
      )}
      {msg && <div className={cn("text-sm", msg.ok ? "text-secondary" : "text-foreground border border-foreground rounded-md px-3 py-2")}>{msg.text}</div>}
      <div className="flex gap-2 justify-end">
        <Button
          type="button"
          variant="outline"
          disabled={pending}
          onClick={() => start(async () => {
            const r = await testDatabase(form);
            setMsg(r.ok ? { ok: true, text: r.note ?? "connection ok" } : { ok: false, text: r.error });
          })}
        >
          Test connection
        </Button>
        <Button type="submit" disabled={pending}>Save & migrate</Button>
      </div>
    </form>
  );
}

function AdminStep({ onDone }: { onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        start(async () => {
          const r = await createAdmin({ name: String(f.get("name")), email: String(f.get("email")), password: String(f.get("password")) });
          if (r.ok) onDone(); else setError(r.error);
        });
      }}
    >
      <p className="text-sm text-muted-foreground">First account, owner of the first organization. Sign-ups after this one are closed.</p>
      <Field label="Name"><input name="name" className={input} required /></Field>
      <Field label="Email"><input name="email" type="email" className={input} required /></Field>
      <Field label="Password"><input name="password" type="password" minLength={8} className={input} required /></Field>
      {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
      <div className="flex justify-end"><Button type="submit" disabled={pending}>Create account</Button></div>
    </form>
  );
}

function OrganizationStep({ onDone }: { onDone: (id: string) => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [touched, setTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => {
          const r = await createFirstOrganization({ name, slug });
          if (r.ok) onDone(r.orgId); else setError(r.error);
        });
      }}
    >
      <p className="text-sm text-muted-foreground">Organizations own projects; projects group apps. You can add more later from the sidebar.</p>
      <Field label="Name"><input value={name} onChange={(e) => { setName(e.target.value); if (!touched) setSlug(slugify(e.target.value)); }} className={input} placeholder="Acme" required autoFocus /></Field>
      <Field label="Slug"><input value={slug} onChange={(e) => { setTouched(true); setSlug(slugify(e.target.value)); }} className={cn(input, "font-mono")} required /></Field>
      {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
      <div className="flex justify-end"><Button type="submit" disabled={pending || !name}>Create organization</Button></div>
    </form>
  );
}

const emptyHost: HostInput = { kind: "github", name: "", baseUrl: "", username: "", token: "", defaultOwner: "" };

function HostsStep({ orgId, oauth }: { orgId: string | null; oauth: OAuthInfo }) {
  const router = useRouter();
  const [manual, setManual] = useState(false);
  const [form, setForm] = useState<HostInput>(emptyHost);
  const [added, setAdded] = useState<{ kind: HostKind; name: string }[]>(oauth.connected ? [{ kind: oauth.connected as HostKind, name: `${oauth.connected} (connected)` }] : []);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const kind = HOST_KINDS.find((k) => k.id === form.kind)!;
  const set = (k: keyof HostInput) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  const finish = () => { router.push("/login"); router.refresh(); };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Where new apps are pushed and releases published. Connect an account, or paste a token. Optional — also under Settings later.</p>

      {oauth.error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{oauth.error}</div>}
      {orgId && (
        <ConnectHosts
          configured={oauth.configured}
          connected={{}}
          origin={oauth.origin}
          orgId={orgId}
          returnTo={`/setup?org=${orgId}`}
          githubApp={oauth.githubApp}
        />
      )}

      <button type="button" onClick={() => setManual((v) => !v)} className="text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground">
        {manual ? "Hide token form" : "Or add a host with a token"}
      </button>

      {added.length > 0 && (
        <ul className="space-y-1 text-sm">
          {added.map((h, i) => (
            <li key={i} className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
              <Check className="size-4" /> <span className="font-medium">{h.name}</span> <span className="text-muted-foreground">{HOST_KINDS.find((k) => k.id === h.kind)?.label}</span>
            </li>
          ))}
        </ul>
      )}

      {manual && <form
        className="space-y-3 rounded-md border border-border p-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!orgId) return setError("organization missing — reload the page");
          start(async () => {
            setError(null);
            const r = await addSetupHost(orgId, { ...form, name: form.name || kind.label });
            if (r.ok) { setAdded([...added, { kind: form.kind, name: form.name || kind.label }]); setForm(emptyHost); } else setError(r.error);
          });
        }}
      >
        <div className="flex gap-1 rounded-md bg-surface-hover p-1 text-sm">
          {HOST_KINDS.map((k) => (
            <button key={k.id} type="button" onClick={() => setForm({ ...emptyHost, kind: k.id })} className={cn("flex-1 rounded px-3 py-1.5", form.kind === k.id ? "bg-foreground text-primary-foreground font-medium" : "text-muted-foreground hover:text-foreground")}>
              {k.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Name"><input value={form.name} onChange={set("name")} className={input} placeholder={kind.label} /></Field>
          <Field label="Default owner"><input value={form.defaultOwner} onChange={set("defaultOwner")} className={cn(input, "font-mono")} placeholder="org or user" /></Field>
          <Field label="Base URL" className="col-span-2"><input value={form.baseUrl} onChange={set("baseUrl")} className={cn(input, "font-mono")} placeholder={kind.baseUrlHint} /></Field>
          {kind.needsUsername && <Field label="Username"><input value={form.username} onChange={set("username")} className={input} required /></Field>}
          <Field label={kind.tokenLabel} hint={kind.tokenHint} className={kind.needsUsername ? "" : "col-span-2"}><input type="password" value={form.token} onChange={set("token")} className={cn(input, "font-mono")} required /></Field>
        </div>
        {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}
        <div className="flex justify-end"><Button type="submit" variant="outline" disabled={pending || !form.token}>Add host</Button></div>
      </form>}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={finish}>{added.length ? "Done" : "Skip for now"}</Button>
        {added.length > 0 && <Button type="button" onClick={finish}>Finish setup</Button>}
      </div>
    </div>
  );
}

const input = "mt-1 w-full h-9 rounded-md border border-border bg-background px-3 text-sm";

function Field({ label, hint, className, children }: { label: string; hint?: string; className?: string; children: React.ReactNode }) {
  return (
    <label className={cn("block text-sm", className)}>
      <span className="text-muted-foreground text-xs">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted-foreground mt-1">{hint}</span>}
    </label>
  );
}
