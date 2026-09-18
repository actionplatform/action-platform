import { v1 } from "./v1";

export type Owner = { account: string; kind: "user" | "org"; repositories: "all" | "selected"; administration: string; contents: string; actions: string; canCreateRepos: boolean; selected?: string[] | null; configureUrl?: string | null };
export type HostAccess =
  | { ok: true; kind: "github" | "gitlab" | "bitbucket"; login: string; installations: Owner[]; installUrl: string | null; problems: string[] }
  | { ok: false; error: string };

export async function hostAccess(_orgId: string, hostId: string): Promise<HostAccess> {
  try {
    return (await v1.hostAccess(hostId)) as HostAccess;
  } catch (e) {
    return { ok: false, error: `${(e as Error).message}; reconnect the host` };
  }
}
