import { credentialsFor } from "./source-hosts";

export type Installation = { account: string; kind: "user" | "org"; repositories: "all" | "selected"; administration: string; contents: string; canCreateRepos: boolean };
export type GithubAccess =
  | { ok: true; login: string; installations: Installation[]; installUrl: string | null; problems: string[] }
  | { ok: false; error: string };

async function get<T>(api: string, token: string, path: string): Promise<{ status: number; body: T | null }> {
  const res = await fetch(`${api}${path}`, { headers: { authorization: `Bearer ${token}`, accept: "application/vnd.github+json", "x-github-api-version": "2022-11-28", "user-agent": "action-platform" }, cache: "no-store" });
  const body = res.ok ? ((await res.json()) as T) : null;
  return { status: res.status, body };
}

export async function githubAccess(orgId: string, hostId: string, appSlug: string | null): Promise<GithubAccess> {
  const creds = await credentialsFor(orgId, hostId);
  if (!creds || creds.kind !== "github") return { ok: false, error: "not a github host" };
  const api = creds.base_url?.replace(/\/$/, "") || "https://api.github.com";

  const me = await get<{ login: string }>(api, creds.token, "/user");
  if (!me.body) return { ok: false, error: `token rejected by GitHub (${me.status}); reconnect the host` };

  const list = await get<{ installations: { account: { login: string; type: string }; repository_selection: string; permissions: Record<string, string> }[] }>(api, creds.token, "/user/installations");
  const installUrl = appSlug ? `https://github.com/apps/${appSlug}/installations/select_target` : null;

  if (list.status === 403 || list.status === 404) {
    return { ok: true, login: me.body.login, installations: [], installUrl, problems: ["This token is not from a GitHub App (personal token): repositories are created with the token's own scopes. Needs `repo` and `workflow`."] };
  }

  const installations: Installation[] = (list.body?.installations ?? []).map((i) => ({
    account: i.account.login,
    kind: i.account.type === "Organization" ? "org" : "user",
    repositories: i.repository_selection === "all" ? "all" : "selected",
    administration: i.permissions.administration ?? "none",
    contents: i.permissions.contents ?? "none",
    canCreateRepos: i.permissions.administration === "write" && i.permissions.contents === "write",
  }));

  const problems: string[] = [];
  if (installations.length === 0) problems.push(`The GitHub App is not installed on any account this token can see. Install it on ${me.body.login} (or the organization that owns the repositories) with access to all repositories.`);
  for (const i of installations) {
    if (i.administration !== "write") problems.push(`${i.account}: repository permission "Administration" is ${i.administration}; it must be "Read and write" to create repositories. Change it in the app's Permissions & events, then accept the new permissions on the installation.`);
    if (i.contents !== "write") problems.push(`${i.account}: repository permission "Contents" is ${i.contents}; it must be "Read and write" to push.`);
    if (i.repositories !== "all") problems.push(`${i.account}: installed on selected repositories only; new repositories created by the platform will not be reachable. Switch the installation to all repositories.`);
  }

  return { ok: true, login: me.body.login, installations, installUrl, problems };
}
