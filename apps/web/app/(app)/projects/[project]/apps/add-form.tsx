"use client";

import { Plus, Wrench } from "lucide-react";
import { call } from "@/lib/call";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";

import { addApp } from "./actions";

const CI = ["github", "gitlab", "jenkins", "bitbucket"];

export function AddForm({ projectId, types, stacks }: { projectId: string; types: { id: string; label: string; description: string }[]; stacks: { id: string; label: string }[] }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsInstall, setNeedsInstall] = useState(false);
  const [type, setType] = useState("web");
  const [ci, setCi] = useState("github");
  const [ciTouched, setCiTouched] = useState(false);
  const [language, setLanguage] = useState("");
  const [pending, start] = useTransition();

  const finish = (r: Awaited<ReturnType<typeof addApp>>, installed: boolean) => {
    if (r.ok) {
      setUrl("");
      setNeedsInstall(false);
      router.push(installed ? `/projects/${projectId}/apps/${r.appId}/configuration` : `/projects/${projectId}/apps/${r.appId}`);
      return;
    }
    if (r.needsInstall) { setNeedsInstall(true); return; }
    setError(r.error);
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); start(async () => { setError(null); finish(await call(() => addApp(projectId, url), (error) => ({ ok: false as const, error }), "The repository may have been added anyway: check the project before trying again."), false); }); }} className="space-y-2">
      <div className="text-xs text-secondary">Add an existing repository</div>
      <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-2">
        <input value={url} onChange={(e) => { setUrl(e.target.value); if (!ciTouched) setCi(e.target.value.includes("gitlab") ? "gitlab" : e.target.value.includes("bitbucket") ? "bitbucket" : "github"); }} placeholder="https://github.com/org/repo.git" className="h-12 w-full min-w-0 px-3.5 font-mono text-base sm:h-9 sm:flex-1 sm:text-sm" required />
        <Button type="submit" variant="outline" disabled={pending} className="h-12 w-full sm:h-9 sm:w-auto"><Plus className="size-4" /> {pending ? "Cloning…" : "Add"}</Button>
      </div>
      {error && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}

      <Dialog
        open={needsInstall}
        onClose={() => !pending && setNeedsInstall(false)}
        title="Install the platform on this repository?"
        description={<>The repository has no <span className="font-mono">platform.toml</span>. The platform can add it, together with <span className="font-mono">.code_quality/</span>, the CI files and the git hooks — the same as <span className="font-mono">action-platform install</span>. Nothing is pushed: you commit the result from Configuration on a branch, with a pull request.</>}
        footer={<><Button variant="ghost" onClick={() => setNeedsInstall(false)} disabled={pending}>Cancel</Button><Button disabled={pending} onClick={() => start(async () => { setError(null); finish(await call(() => addApp(projectId, url, { type, ci, language: language || null }), (error) => ({ ok: false as const, error }), "The repository may have been added anyway: check the project before trying again."), true); })}><Wrench className="size-4" strokeWidth={1.75} /> {pending ? "Installing…" : "Install and add"}</Button></>}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Project type</span>
            <Select value={type} onChange={setType} options={types.map((t) => ({ value: t.id, label: t.label, hint: t.description }))} />
          </label>
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Language</span>
            <Select value={language} onChange={setLanguage} options={[{ value: "", label: "Detect automatically" }, ...stacks.map((m) => ({ value: m.id, label: m.label })), { value: "none", label: "None (config only)" }]} />
          </label>
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">CI</span>
            <Select value={ci} onChange={(v) => { setCiTouched(true); setCi(v); }} options={CI.map((c) => ({ value: c, label: c }))} />
          </label>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Detection reads pyproject.toml, go.mod, package.json… or the source files. Without a language only platform.toml, CI and hooks are added.</p>
      </Dialog>
    </form>
  );
}
