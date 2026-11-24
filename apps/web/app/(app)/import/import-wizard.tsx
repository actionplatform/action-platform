"use client";

import { Archive, Check, FolderGit2, KanbanSquare, Lock, RefreshCw, Users, UserRound } from "lucide-react";
import Link from "next/link";
import { call } from "@/lib/call";
import { useEffect, useMemo, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { type ImportOrganizations, type ImportPreview, type ImportSummary, importJob, loadOrganizations, loadPreview, startImport } from "./actions";

type Host = { id: string; kind: string; name: string; login: string | null };
type RoleOption = { id: string; label: string };
type ProjectOption = { id: string; name: string };

const PEOPLE_STATUS: Record<string, { label: string; hint: string; selectable: boolean }> = {
  member: { label: "Member", hint: "already in this organization", selectable: false },
  user: { label: "Has account", hint: "added as a member right away", selectable: true },
  invited: { label: "Invited", hint: "an invitation is already pending", selectable: false },
  invitable: { label: "Invite", hint: "receives an invitation, by email when the instance sends email", selectable: true },
  invitable_login: { label: "Invite by login", hint: "invited by login; they verify it when they accept", selectable: true },
  no_email: { label: "No email", hint: "no public email, and no OAuth app for this host on the platform to verify a login; invite by hand", selectable: false },
};

type HostRole = "org_admin" | "team_maintainer" | "member";

const KINDS: Record<string, { label: string; org: string; projects: string; via: string; roles: Record<HostRole, string>; badge: Record<HostRole, string> }> = {
  github: { label: "GitHub", org: "Organization", projects: "GitHub Projects", via: "via GitHub Project", roles: { org_admin: "Organization owners", team_maintainer: "Team maintainers", member: "Members" }, badge: { org_admin: "GitHub owner", team_maintainer: "team maintainer", member: "" } },
  gitlab: { label: "GitLab", org: "Group", projects: "Subgroups", via: "via subgroup", roles: { org_admin: "Group owners", team_maintainer: "Maintainers", member: "Developers and below" }, badge: { org_admin: "GitLab owner", team_maintainer: "maintainer", member: "" } },
  bitbucket: { label: "Bitbucket", org: "Workspace", projects: "Bitbucket projects", via: "via Bitbucket project", roles: { org_admin: "Workspace owners", team_maintainer: "Maintainers", member: "Members" }, badge: { org_admin: "workspace owner", team_maintainer: "maintainer", member: "" } },
};
const HOST_ROLES: HostRole[] = ["org_admin", "team_maintainer", "member"];

function Row({ id, checked, disabled, onToggle, children }: { id: string; checked: boolean; disabled?: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <li className={cn("flex items-start gap-3 px-4 py-3", disabled && "opacity-60")}>
      <input id={id} type="checkbox" className="mt-1 size-4 shrink-0 accent-foreground" checked={checked} disabled={disabled} onChange={onToggle} />
      <label htmlFor={id} className={cn("min-w-0 flex-1", !disabled && "cursor-pointer")}>{children}</label>
    </li>
  );
}

function AdoptionLink({ project, result }: { project: ProjectOption | undefined; result: ImportSummary | null }) {
  if (!result || result.apps.length + result.projects.length === 0) return null;
  const count = project ? result.apps.filter((a) => a.endsWith(`→ ${project.name}`)).length : 0;
  if (!project || count === 0) return <p className="basis-full text-[13px] text-secondary">To open install pull requests, use Adoption on each imported project.</p>;
  return <Link href={`/projects/${project.id}/adoption`}><Button variant="outline">Open install pull requests for {count} {count === 1 ? "repository" : "repositories"}</Button></Link>;
}

function useSelection(all: string[]) {
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const toggle = (key: string) => setPicked((s) => { const n = new Set(s); if (n.has(key)) n.delete(key); else n.add(key); return n; });
  const allPicked = all.length > 0 && all.every((k) => picked.has(k));
  const toggleAll = () => setPicked(allPicked ? new Set() : new Set(all));
  return { picked, toggle, toggleAll, allPicked, reset: () => setPicked(new Set()) };
}

export function ImportWizard({ hosts, roles, projects, canManage }: { hosts: Host[]; roles: RoleOption[]; projects: ProjectOption[]; canManage: boolean }) {
  const importable = hosts.filter((h) => h.kind in KINDS);
  const [hostId, setHostId] = useState(importable[0]?.id ?? "");
  const kind = KINDS[importable.find((h) => h.id === hostId)?.kind ?? "github"] ?? KINDS.github;
  const [orgs, setOrgs] = useState<ImportOrganizations | null>(null);
  const [login, setLogin] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [projectId, setProjectId] = useState("");
  const [projectTargets, setProjectTargets] = useState<Record<string, string>>({});
  const fallback = roles.find((r) => r.id === "developer")?.id ?? roles[0]?.id ?? "developer";
  const [mapping, setMapping] = useState<Record<HostRole, string>>({ org_admin: fallback, team_maintainer: fallback, member: fallback });
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<{ id: string; status: string; result: ImportSummary | null; error: string | null } | null>(null);
  const [loadingOrgs, startOrgs] = useTransition();
  const [loadingPreview, startPreview] = useTransition();
  const [submitting, startSubmit] = useTransition();

  const repoKeys = useMemo(() => (preview?.repositories ?? []).filter((r) => !r.imported_as).map((r) => r.full_name), [preview]);
  const projectKeys = useMemo(() => (preview?.projects ?? []).map((p) => String(p.number)), [preview]);
  const teamKeys = useMemo(() => (preview?.teams ?? []).map((t) => t.slug), [preview]);
  const peopleKeys = useMemo(() => (preview?.people ?? []).filter((p) => PEOPLE_STATUS[p.status]?.selectable).map((p) => p.login), [preview]);
  const repos = useSelection(repoKeys);
  const ghProjects = useSelection(projectKeys);
  const teams = useSelection(teamKeys);
  const people = useSelection(peopleKeys);

  useEffect(() => {
    if (!hostId || !canManage) return;
    setOrgs(null); setLogin(""); setPreview(null); setError(null);
    startOrgs(async () => {
      const r = await loadOrganizations(hostId);
      if (r.ok) setOrgs(r.data); else setError(r.error);
    });
  }, [hostId, canManage]);

  useEffect(() => {
    if (!login) { setPreview(null); return; }
    setPreview(null); setError(null); setOverrides({}); repos.reset(); ghProjects.reset(); teams.reset(); people.reset();
    startPreview(async () => {
      const r = await loadPreview(hostId, login);
      if (r.ok) setPreview(r.data); else setError(r.error);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [login]);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const timer = setInterval(async () => {
      const r = await call(() => importJob(job.id), (error) => ({ ok: false as const, error }));
      if (r.ok) setJob({ id: job.id, ...r.data });
    }, 2000);
    return () => clearInterval(timer);
  }, [job]);

  const linked = useMemo(() => new Set((preview?.projects ?? []).filter((p) => ghProjects.picked.has(String(p.number))).flatMap((p) => p.repositories)), [preview, ghProjects.picked]);

  if (!canManage) {
    return <Panel><PanelBody className="text-sm text-secondary">Importing needs the admin role in this organization.</PanelBody></Panel>;
  }

  if (importable.length === 0) {
    return (
      <Panel>
        <PanelBody className="space-y-3 text-sm">
          <p className="text-secondary">No GitHub, GitLab or Bitbucket host is connected to this organization yet.</p>
          <Link href="/settings"><Button>Connect a code host in Settings</Button></Link>
        </PanelBody>
      </Panel>
    );
  }

  const total = repos.picked.size + ghProjects.picked.size + teams.picked.size + people.picked.size;

  const submit = () => startSubmit(async () => {
    setError(null);
    const r = await call(() => startImport({ host_id: hostId, organization: login, repositories: [...repos.picked].filter((r) => !linked.has(r)), projects: (preview?.projects ?? []).filter((p) => ghProjects.picked.has(String(p.number))).map((p) => ({ number: p.number, project_id: projectTargets[String(p.number)] || null })), teams: [...teams.picked], people: [...people.picked], role: mapping.member, roles: { org_admin: mapping.org_admin, team_maintainer: mapping.team_maintainer }, people_roles: Object.fromEntries(Object.entries(overrides).filter(([l]) => people.picked.has(l))), project_id: projectId || null }), (error) => ({ ok: false as const, error }), "The import may have started anyway: check Projects before trying again.");
    if (r.ok) setJob({ id: r.data.job, status: "queued", result: null, error: null }); else setError(r.error);
  });

  if (job) {
    const running = job.status !== "done" && job.status !== "failed";
    return (
      <Panel>
        <PanelHeader title={running ? `Importing ${login}…` : job.status === "done" ? `Imported ${login}` : `Import of ${login} failed`} aside={running && <RefreshCw className="size-4 animate-spin text-secondary" strokeWidth={1.75} aria-hidden="true" />} />
        <PanelBody className="space-y-4 text-sm">
          {running && <p className="text-secondary">Cloning repositories and creating projects, teams and invitations. This page updates by itself; you can leave it.</p>}
          {job.error && <div className="rounded-md border border-foreground px-3 py-2">{job.error}</div>}
          {job.result && (
            <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {([["Projects", job.result.projects], ["Apps", job.result.apps], ["Teams", job.result.teams], ["Members", job.result.members], ["Invited by email", job.result.invitations], ["Invited by login", job.result.login_invitations ?? []]] as const).filter(([label, rows]) => rows.length > 0 || label !== "Apps").map(([label, rows]) => (
                <div key={label} className="rounded-md border border-border px-3 py-2">
                  <dt className="text-xs text-secondary">{label}</dt>
                  <dd className="text-lg font-semibold">{rows.length}</dd>
                  {rows.length > 0 && <dd className="mt-1 truncate text-xs text-secondary" title={rows.join(", ")}>{rows.join(", ")}</dd>}
                </div>
              ))}
            </dl>
          )}
          {job.result && (job.result.waiting ?? []).length > 0 && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-secondary">Teams waiting for invitees</h3>
              <ul className="space-y-1 text-xs text-secondary">{(job.result.waiting ?? []).map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
          )}
          {job.result && job.result.skipped.length > 0 && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-secondary">Skipped</h3>
              <ul className="space-y-1 font-mono text-xs text-secondary">{job.result.skipped.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
          )}
          {!running && (
            <div className="flex flex-wrap gap-2">
              <Link href="/projects"><Button>Open projects</Button></Link>
              <AdoptionLink project={projects.find((p) => p.id === projectId)} result={job.result} />
              <Button variant="ghost" onClick={() => { setJob(null); setLogin(""); }}>Import another</Button>
            </div>
          )}
        </PanelBody>
      </Panel>
    );
  }

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader title="Source" />
        <PanelBody className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-secondary">Code host</span>
            <Select value={hostId} onChange={setHostId} options={importable.map((h) => ({ value: h.id, label: h.name, hint: [KINDS[h.kind]?.label, h.login].filter(Boolean).join(" · ") || undefined }))} />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-secondary">{kind.org}</span>
            <Select value={login} onChange={setLogin} disabled={loadingOrgs || !orgs} placeholder={loadingOrgs ? "Loading…" : "Pick an organization"} options={(orgs?.organizations ?? []).map((o) => ({ value: o.login, label: o.login, hint: o.kind === "user" ? "personal account" : o.name !== o.login ? o.name : undefined }))} />
          </label>
          {orgs && (
            <p className="text-[13px] text-secondary md:col-span-2">
              Only organizations the connected host can see are listed.
              {orgs.install_url ? <> Missing one? <a href={orgs.install_url} target="_blank" rel="noreferrer" className="underline underline-offset-4 hover:text-foreground">Install the GitHub App on it</a>, then reload.</> : kind === KINDS.github ? <> Missing one? Reconnect the host with the <code className="font-mono">read:org</code> scope in Settings.</> : null}
            </p>
          )}
        </PanelBody>
      </Panel>

      {error && <div className="rounded-md border border-foreground px-3 py-2 text-sm">{error}</div>}
      {loadingPreview && <Panel><PanelBody className="flex items-center gap-2 text-sm text-secondary"><RefreshCw className="size-4 animate-spin" strokeWidth={1.75} aria-hidden="true" />Reading {login} on {kind.label}…</PanelBody></Panel>}

      {preview && (
        <>
          {preview.limits.length > 0 && (
            <div className="space-y-1 rounded-md border border-border px-3 py-2 text-[13px] text-secondary">
              {preview.limits.map((l) => <p key={l}>{l}</p>)}
            </div>
          )}
          {preview.problems.length > 0 && (
            <div className="space-y-1 rounded-md border border-foreground px-3 py-2 text-sm">
              {preview.problems.map((p) => <p key={p}>{p}</p>)}
            </div>
          )}
          {preview.projects.length > 0 && (
            <Panel>
              <PanelHeader
                title={`${kind.projects} · ${preview.projects.length}`}
                aside={<button type="button" className="text-xs text-secondary hover:text-foreground" onClick={ghProjects.toggleAll}>{ghProjects.allPicked ? "Clear" : "Select all"}</button>}
              />
              <ul className="divide-y divide-border">
                {preview.projects.map((p) => (
                  <Row key={p.number} id={`gh-project-${p.number}`} checked={ghProjects.picked.has(String(p.number))} onToggle={() => ghProjects.toggle(String(p.number))}>
                    <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                      <KanbanSquare className="size-4 text-secondary" strokeWidth={1.75} aria-hidden="true" />{p.title}
                      {p.closed && <Badge>closed</Badge>}
                      {p.exists && !projectTargets[String(p.number)] && <Badge tone="ok">exists · apps are added to it</Badge>}
                      {ghProjects.picked.has(String(p.number)) && (
                        <span className="ml-auto" onClick={(e) => e.preventDefault()}>
                          <Select size="sm" value={projectTargets[String(p.number)] ?? ""} onChange={(v) => setProjectTargets((t) => ({ ...t, [String(p.number)]: v }))} aria-label={`Platform project for ${p.title}`} options={[{ value: "", label: p.exists ? `Into ${p.title}` : `New project ${p.title}` }, ...projects.map((pr) => ({ value: pr.id, label: `Into ${pr.name}` }))]} />
                        </span>
                      )}
                    </div>
                    <div className="text-[13px] text-secondary">{p.repositories.length === 0 ? "No repositories linked" : `${p.repositories.length} linked ${p.repositories.length === 1 ? "repository becomes its app" : "repositories become its apps"}: ${p.repositories.map((r) => r.split("/")[1]).join(", ")}`}{p.description ? ` · ${p.description}` : ""}</div>
                  </Row>
                ))}
              </ul>
            </Panel>
          )}

          <Panel>
            <PanelHeader
              title={`Repositories · ${preview.repositories.length}`}
              aside={
                <div className="flex items-center gap-3">
                  <Select size="sm" value={projectId} onChange={setProjectId} aria-label="Project the apps go into" options={[{ value: "", label: "One project per repository" }, ...projects.map((p) => ({ value: p.id, label: `Into ${p.name}` }))]} />
                  {repoKeys.length > 0 && <button type="button" className="text-xs text-secondary hover:text-foreground" onClick={repos.toggleAll}>{repos.allPicked ? "Clear" : "Select all"}</button>}
                </div>
              }
            />
            <ul className="divide-y divide-border">
              {preview.repositories.length === 0 && <li className="px-4 py-6 text-center text-sm text-secondary">No repositories.</li>}
              {preview.repositories.map((r) => (
                <Row key={r.full_name} id={`repo-${r.full_name}`} checked={repos.picked.has(r.full_name) || (linked.has(r.full_name) && !r.imported_as)} disabled={!!r.imported_as || linked.has(r.full_name)} onToggle={() => repos.toggle(r.full_name)}>
                  <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    <FolderGit2 className="size-4 text-secondary" strokeWidth={1.75} aria-hidden="true" />{r.name}
                    {r.private && <Lock className="size-3.5 text-secondary" strokeWidth={1.75} aria-label="private" />}
                    {r.archived && <Badge><Archive className="mr-1 size-3" strokeWidth={1.75} aria-hidden="true" />archived</Badge>}
                    {r.fork && <Badge>fork</Badge>}
                    {r.language && <Badge>{r.language}</Badge>}
                    {r.imported_as && <Badge tone="ok"><Check className="mr-1 size-3" strokeWidth={1.75} aria-hidden="true" />imported as {r.imported_as}</Badge>}
                    {!r.imported_as && linked.has(r.full_name) && <Badge tone="ok">{kind.via}</Badge>}
                  </div>
                  {r.description && <div className="text-[13px] text-secondary">{r.description}</div>}
                </Row>
              ))}
            </ul>
          </Panel>

          <Panel>
            <PanelHeader
              title={`Teams · ${preview.teams.length}`}
              aside={teamKeys.length > 0 && <button type="button" className="text-xs text-secondary hover:text-foreground" onClick={teams.toggleAll}>{teams.allPicked ? "Clear" : "Select all"}</button>}
            />
            <ul className="divide-y divide-border">
              {preview.teams.length === 0 && <li className="px-4 py-6 text-center text-sm text-secondary">No teams{preview.people.length === 1 ? " on a personal account" : ""}.</li>}
              {preview.teams.map((t) => (
                <Row key={t.slug} id={`team-${t.slug}`} checked={teams.picked.has(t.slug)} onToggle={() => teams.toggle(t.slug)}>
                  <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    <Users className="size-4 text-secondary" strokeWidth={1.75} aria-hidden="true" />{t.name}
                    {t.exists && <Badge tone="ok">exists · members and projects are added</Badge>}
                  </div>
                  <div className="text-[13px] text-secondary">{t.members.length} people · {t.repositories.length} repositories{t.description ? ` · ${t.description}` : ""}</div>
                </Row>
              ))}
            </ul>
          </Panel>

          <Panel>
            <PanelHeader
              title={`People · ${preview.people.length}`}
              aside={
                <div className="flex items-center gap-3">
                  {peopleKeys.length > 0 && <button type="button" className="text-xs text-secondary hover:text-foreground" onClick={people.toggleAll}>{people.allPicked ? "Clear" : "Select all"}</button>}
                </div>
              }
            />
            <div className="grid gap-3 border-b border-border px-4 py-3 md:grid-cols-3">
              {HOST_ROLES.map((h) => (
                <label key={h} className="block text-sm">
                  <span className="mb-1 block text-xs text-secondary">{kind.roles[h]} on {kind.label} become</span>
                  <Select size="sm" value={mapping[h]} onChange={(v) => setMapping((m) => ({ ...m, [h]: v }))} options={roles.map((r) => ({ value: r.id, label: r.label }))} aria-label={`Platform role for ${kind.roles[h].toLowerCase()}`} />
                </label>
              ))}
            </div>
            <ul className="divide-y divide-border">
              {preview.people.map((p) => {
                const status = PEOPLE_STATUS[p.status] ?? { label: p.status, hint: "", selectable: false };
                const hostRole = HOST_ROLES.find((h) => h === p.role) ?? "member";
                const picked = people.picked.has(p.login);
                return (
                  <Row key={p.login} id={`person-${p.login}`} checked={picked} disabled={!status.selectable} onToggle={() => people.toggle(p.login)}>
                    <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                      <UserRound className="size-4 text-secondary" strokeWidth={1.75} aria-hidden="true" />{p.name}
                      <span className="font-mono text-xs text-secondary">@{p.login}</span>
                      <Badge tone={p.status === "member" ? "ok" : "neutral"}>{status.label}</Badge>
                      {hostRole !== "member" && <Badge>{kind.badge[hostRole]}</Badge>}
                      {picked && (
                        <span className="ml-auto" onClick={(e) => e.preventDefault()}>
                          <Select size="sm" value={overrides[p.login] ?? mapping[hostRole]} onChange={(v) => setOverrides((o) => ({ ...o, [p.login]: v }))} options={roles.map((r) => ({ value: r.id, label: r.label }))} aria-label={`Role for ${p.login}`} />
                        </span>
                      )}
                    </div>
                    <div className="text-[13px] text-secondary">{p.email ?? "no public email"} · {status.hint}</div>
                  </Row>
                );
              })}
            </ul>
          </Panel>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-secondary">{total === 0 ? "Pick projects, repositories, teams or people." : `${ghProjects.picked.size} projects, ${repos.picked.size + [...linked].filter((r) => !repos.picked.has(r)).length} repositories, ${teams.picked.size} teams, ${people.picked.size} people.`} People invited join their teams when they accept; people already in the organization keep their role.</p>
            <Button disabled={total === 0 || submitting} onClick={submit}>{submitting ? "Starting…" : "Import"}</Button>
          </div>
        </>
      )}
    </div>
  );
}
