"use client";

import { ArrowRight, Plus, TriangleAlert, Wrench } from "lucide-react";
import { call } from "@/lib/call";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/copy-button";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";

import { addApp, type InstallReport } from "@/features/projects/actions";

const CI = [{ value: "", label: "Detect from the repository" }, { value: "github", label: "GitHub Actions" }, { value: "gitlab", label: "GitLab CI" }, { value: "jenkins", label: "Jenkins" }, { value: "bitbucket", label: "Bitbucket Pipelines" }, { value: "none", label: "No CI" }];
const CI_FILE: Record<string, string> = { github: ".github/workflows", gitlab: ".gitlab-ci.yml", jenkins: "Jenkinsfile", bitbucket: "bitbucket-pipelines.yml" };

function ciLabel(ci: string): string {
  return CI.find((c) => c.value === ci)?.label ?? ci;
}

export function needsReview(report: InstallReport | null): report is InstallReport {
  return !!report && (report.detected_ci.length > 0 || report.warnings.length > 0 || !!report.ci_snippet);
}

export function AddForm({ projectId, types, stacks }: { projectId: string; types: { id: string; label: string; description: string }[]; stacks: { id: string; label: string }[] }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsInstall, setNeedsInstall] = useState(false);
  const [type, setType] = useState("web");
  const [ci, setCi] = useState("");
  const [language, setLanguage] = useState("");
  const [report, setReport] = useState<{ appId: string; report: InstallReport } | null>(null);
  const [pending, start] = useTransition();

  const configuration = (appId: string) => `/projects/${projectId}/apps/${appId}/configuration`;
  const finish = (r: Awaited<ReturnType<typeof addApp>>, installed: boolean) => {
    if (r.ok) {
      setUrl("");
      if (installed && needsReview(r.report)) { setReport({ appId: r.appId, report: r.report }); return; }
      setNeedsInstall(false);
      router.push(installed ? configuration(r.appId) : `/projects/${projectId}/apps/${r.appId}`);
      return;
    }
    if (r.needsInstall) { setNeedsInstall(true); return; }
    setError(r.error);
  };
  const close = () => { if (pending) return; setNeedsInstall(false); setReport(null); setError(null); };

  return (
    <form onSubmit={(e) => { e.preventDefault(); start(async () => { setError(null); finish(await call(() => addApp(projectId, url), (error) => ({ ok: false as const, error }), "The repository may have been added anyway: check the project before trying again."), false); }); }} className="space-y-2">
      <div className="text-xs text-secondary">Add an existing repository</div>
      <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-2">
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/org/repo.git" className="h-12 w-full min-w-0 px-3.5 font-mono text-base sm:h-9 sm:flex-1 sm:text-sm" required />
        <Button type="submit" variant="outline" disabled={pending} className="h-12 w-full sm:h-9 sm:w-auto"><Plus className="size-4" /> {pending ? "Cloning…" : "Add"}</Button>
      </div>
      {error && !needsInstall && <div className="text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</div>}

      <Dialog
        open={needsInstall && !report}
        onClose={close}
        title="Install the platform on this repository?"
        description={<>The repository has no <span className="font-mono">platform.toml</span>. The platform can add it, together with <span className="font-mono">.code_quality/</span>, the CI files and the git hooks — the same as <span className="font-mono">action-platform install</span>. Nothing is pushed: you commit the result from Configuration on a branch, with a pull request.</>}
        footer={<><Button variant="ghost" onClick={close} disabled={pending}>Cancel</Button><Button disabled={pending} onClick={() => start(async () => { setError(null); finish(await call(() => addApp(projectId, url, { type, ci: ci || null, language: language || null }), (error) => ({ ok: false as const, error }), "The repository may have been added anyway: check the project before trying again."), true); })}><Wrench className="size-4" strokeWidth={1.75} /> {pending ? "Installing…" : "Install and add"}</Button></>}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Project type</span>
            <Select value={type} onChange={setType} options={types.map((t) => ({ value: t.id, label: t.label, hint: t.description }))} />
          </label>
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">Language</span>
            <Select value={language} onChange={setLanguage} options={[{ value: "", label: "Detect automatically" }, ...stacks.map((m) => ({ value: m.id, label: m.label })), { value: "none", label: "None (config only)" }]} />
          </label>
          <label className="block text-sm"><span className="mb-1 block text-xs text-secondary">CI</span>
            <Select value={ci} onChange={setCi} options={CI} />
          </label>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Detection reads pyproject.toml, go.mod, package.json… or the source files. The CI comes from the files the repository already has (Jenkinsfile, .gitlab-ci.yml, bitbucket-pipelines.yml, .github/workflows), else from where it is hosted; with two of them, pick one. Without a language only platform.toml, CI and hooks are added; with No CI, no pipeline files at all — git-flow is still enforced by the hooks.</p>
        {error && <p role="alert" className="mt-3 text-sm text-foreground border border-foreground rounded-md px-3 py-2">{error}</p>}
      </Dialog>

      <Dialog
        open={!!report}
        onClose={close}
        title="Platform installed — review before committing"
        description={<>The files are drafts on the app. Check what the installer found, then commit them from Configuration.</>}
        footer={report && <Button onClick={() => router.push(configuration(report.appId))}>Open configuration <ArrowRight className="size-4" /></Button>}
      >
        {report && (
          <div className="space-y-3 text-sm">
            <p>CI: <span className="font-medium">{ciLabel(report.report.ci)}</span>{report.report.detected_ci.length > 0 && <span className="text-secondary"> · found in the repository: <span className="font-mono">{report.report.detected_ci.map((d) => CI_FILE[d] ?? d).join(", ")}</span></span>}</p>
            {report.report.warnings.map((w) => (
              <p key={w} className="flex items-start gap-2 text-secondary"><TriangleAlert className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} /> {w}</p>
            ))}
            {report.report.ci_snippet && (
              <div className="space-y-2">
                <p className="text-secondary">The Jenkinsfile is kept. Load the library at its top and add these stages to its pipeline to run the platform&apos;s checks:</p>
                <div className="relative rounded-md border border-border-subtle bg-background">
                  <div className="absolute right-1 top-1"><CopyButton text={report.report.ci_snippet} label="Copy stages" size="icon" /></div>
                  <pre className="max-h-64 overflow-auto p-3 pr-10 font-mono text-xs leading-5 text-secondary">{report.report.ci_snippet}</pre>
                </div>
              </div>
            )}
          </div>
        )}
      </Dialog>
    </form>
  );
}
