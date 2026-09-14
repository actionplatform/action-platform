import { PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { credentialsFor, setHostOwner } from "./source-hosts";

export type Owner = { account: string; kind: "user" | "org"; repositories: "all" | "selected"; administration: string; contents: string; canCreateRepos: boolean; selected?: string[]; configureUrl?: string | null };
export type HostAccess =
  | { ok: true; kind: "github" | "gitlab" | "bitbucket"; login: string; installations: Owner[]; installUrl: string | null; problems: string[] }
  | { ok: false; error: string };

async function get<T>(url: string, headers: Record<string, string>): Promise<{ status: number; body: T | null }> {
  const res = await fetch(url, { headers: { accept: "application/json", "user-agent": "action-platform", ...headers }, cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS) });
  const body = res.ok ? ((await res.json()) as T) : null;
  return { status: res.status, body };
}

export async function hostAccess(orgId: string, hostId: string, githubAppSlug: string | null): Promise<HostAccess> {
  const creds = await credentialsFor(orgId, hostId);
  if (!creds) return { ok: false, error: "no credentials" };
  if (creds.kind === "github") return github(creds.token, creds.base_url, githubAppSlug);
  if (creds.kind === "gitlab") return gitlab(creds.token, creds.base_url);
  if (creds.kind === "bitbucket") return healedOwner(orgId, hostId, creds.owner, await bitbucket(creds.token, creds.username));
  return { ok: false, error: `no access check for ${creds.kind}` };
}

async function healedOwner(orgId: string, hostId: string, owner: string | null, access: HostAccess): Promise<HostAccess> {
  if (!access.ok || access.installations.length === 0) return access;
  const slugs = access.installations.map((i) => i.account);
  if (owner && slugs.includes(owner)) return access;
  const first = access.installations.find((i) => i.canCreateRepos) ?? access.installations[0];
  await setHostOwner(orgId, hostId, first.account);
  return access;
}

async function github(token: string, baseUrl: string | null, appSlug: string | null): Promise<HostAccess> {
  const api = baseUrl?.replace(/\/$/, "") || "https://api.github.com";
  const headers = { authorization: `Bearer ${token}`, "x-github-api-version": "2022-11-28" };
  const me = await get<{ login: string }>(`${api}/user`, headers);
  if (!me.body) return { ok: false, error: `token rejected by GitHub (${me.status}); reconnect the host` };

  const list = await get<{ installations: { id: number; account: { login: string; type: string }; repository_selection: string; permissions: Record<string, string> }[] }>(`${api}/user/installations`, headers);
  const installUrl = appSlug ? `https://github.com/apps/${appSlug}/installations/select_target` : null;

  if (list.status === 403 || list.status === 404) {
    return { ok: true, kind: "github", login: me.body.login, installations: [], installUrl, problems: ["This token is not from a GitHub App (personal token): repositories are created with the token's own scopes. Needs `repo` and `workflow`."] };
  }

  const installations: Owner[] = await Promise.all(
    (list.body?.installations ?? []).map(async (i) => {
      const org = i.account.type === "Organization";
      const selected = i.repository_selection === "all" ? undefined : await selectedRepositories(api, headers, i.id);
      return {
        account: i.account.login,
        kind: org ? "org" : "user",
        repositories: i.repository_selection === "all" ? "all" : "selected",
        administration: i.permissions.administration ?? "none",
        contents: i.permissions.contents ?? "none",
        canCreateRepos: i.permissions.administration === "write" && i.permissions.contents === "write",
        selected,
        configureUrl: org ? `https://github.com/organizations/${i.account.login}/settings/installations/${i.id}` : `https://github.com/settings/installations/${i.id}`,
      } as Owner;
    }),
  );

  const problems: string[] = [];
  if (installations.length === 0) problems.push(`The GitHub App is not installed on any account this token can see. Install it on ${me.body.login} (or the organization that owns the repositories) with access to all repositories.`);
  for (const i of installations) {
    if (i.administration !== "write") problems.push(`${i.account}: repository permission "Administration" is ${i.administration}; it must be "Read and write" to create repositories. Change it in the app's Permissions & events, then accept the new permissions on the installation.`);
    if (i.contents !== "write") problems.push(`${i.account}: repository permission "Contents" is ${i.contents}; it must be "Read and write" to push.`);
    if (i.repositories !== "all") problems.push(`${i.account}: installed on selected repositories only; new repositories created by the platform will not be reachable. Switch the installation to all repositories.`);
  }

  return { ok: true, kind: "github", login: me.body.login, installations, installUrl, problems };
}

async function selectedRepositories(api: string, headers: Record<string, string>, installationId: number): Promise<string[]> {
  const res = await get<{ repositories: { full_name: string }[] }>(`${api}/user/installations/${installationId}/repositories?per_page=100`, headers);
  return (res.body?.repositories ?? []).map((r) => r.full_name);
}

async function gitlab(token: string, baseUrl: string | null): Promise<HostAccess> {
  const api = (baseUrl?.replace(/\/$/, "") || "https://gitlab.com/api/v4").replace(/\/api\/v4$/, "") + "/api/v4";
  const headers = { authorization: `Bearer ${token}` };
  const me = await get<{ username: string; can_create_project?: boolean }>(`${api}/user`, headers);
  if (!me.body) return { ok: false, error: `token rejected by GitLab (${me.status}); reconnect the host` };

  const groups = await get<{ full_path: string; access_level?: number }[]>(`${api}/groups?min_access_level=30&per_page=100&order_by=path`, headers);
  const installations: Owner[] = [
    { account: me.body.username, kind: "user", repositories: "all", administration: me.body.can_create_project === false ? "none" : "write", contents: "write", canCreateRepos: me.body.can_create_project !== false },
    ...(groups.body ?? []).map((g) => ({ account: g.full_path, kind: "org" as const, repositories: "all" as const, administration: "write", contents: "write", canCreateRepos: true })),
  ];
  const problems: string[] = [];
  if (me.body.can_create_project === false) problems.push(`${me.body.username} cannot create projects in the personal namespace; pick a group instead.`);
  if (groups.status !== 200) problems.push("Could not list groups: the token needs the `api` scope.");

  return { ok: true, kind: "gitlab", login: me.body.username, installations, installUrl: null, problems };
}

async function bitbucket(token: string, username: string | null): Promise<HostAccess> {
  const auth = username ? `Basic ${Buffer.from(`${username}:${token}`).toString("base64")}` : `Bearer ${token}`;
  const me = await get<{ username: string }>("https://api.bitbucket.org/2.0/user", { authorization: auth });
  if (!me.body) return { ok: false, error: `token rejected by Bitbucket (${me.status}); reconnect the host` };

  const spaces = await get<{ values: { workspace: { slug: string }; permission: string }[] }>("https://api.bitbucket.org/2.0/user/permissions/workspaces?pagelen=100", { authorization: auth });
  let installations: Owner[] = (spaces.body?.values ?? []).map((w) => ({
    account: w.workspace.slug,
    kind: "org" as const,
    repositories: "all" as const,
    administration: w.permission === "owner" || w.permission === "collaborator" ? "write" : "none",
    contents: "write",
    canCreateRepos: w.permission === "owner" || w.permission === "collaborator",
  }));

  if (installations.length === 0) {
    const member = await get<{ values: { slug: string }[] }>("https://api.bitbucket.org/2.0/workspaces?role=member&pagelen=100", { authorization: auth });
    installations = (member.body?.values ?? []).map((w) => ({ account: w.slug, kind: "org" as const, repositories: "all" as const, administration: "write", contents: "write", canCreateRepos: true }));
  }

  const problems: string[] = [];
  if (installations.length === 0) problems.push(`Bitbucket lists no workspace for this account (permissions endpoint answered ${spaces.status}). The OAuth consumer needs Workspace membership: Read and Account: Read; repositories are created inside a workspace, never under the account name.`);

  return { ok: true, kind: "bitbucket", login: me.body.username, installations, installUrl: null, problems };
}
