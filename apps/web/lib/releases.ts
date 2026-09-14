import { PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { and, desc, eq } from "drizzle-orm";
import { newId, q } from "./db/query";
import { type Credentials, credentialsFor } from "./source-hosts";

export type StoredRelease = {
  id: string;
  appId: string;
  tag: string;
  name: string | null;
  body: string | null;
  url: string | null;
  author: string | null;
  sha: string | null;
  prerelease: boolean;
  draft: boolean;
  publishedAt: Date | null;
  source: string;
  syncedAt: Date;
};

type Remote = Omit<StoredRelease, "id" | "appId" | "syncedAt">;

export async function releasesOf(appId: string): Promise<StoredRelease[]> {
  const { db, t } = await q();
  return db.select().from(t.release).where(eq(t.release.appId, appId)).orderBy(desc(t.release.publishedAt));
}

export async function syncReleases(orgId: string, appId: string, sourceHostId: string | null, repo: string | null): Promise<{ ok: true; count: number } | { ok: false; error: string }> {
  if (!sourceHostId || !repo) return { ok: false, error: "no source host" };
  const creds = await credentialsFor(orgId, sourceHostId);
  if (!creds) return { ok: false, error: "no credentials" };

  let remote: Remote[];
  try {
    remote = await fetchRemote(creds, repo);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }

  const { db, t } = await q();
  const existing = await db.select({ id: t.release.id, tag: t.release.tag }).from(t.release).where(eq(t.release.appId, appId));
  const byTag = new Map(existing.map((r) => [r.tag, r.id]));
  const now = new Date();

  for (const r of remote) {
    const id = byTag.get(r.tag);
    if (id) {
      await db.update(t.release).set({ ...r, syncedAt: now }).where(and(eq(t.release.id, id), eq(t.release.appId, appId)));
    } else {
      await db.insert(t.release).values({ id: newId(), appId, ...r, syncedAt: now });
    }
  }

  return { ok: true, count: remote.length };
}

async function fetchRemote(creds: Credentials, repo: string): Promise<Remote[]> {
  if (creds.kind === "github") return github(creds, repo);
  if (creds.kind === "gitlab") return gitlab(creds, repo);
  if (creds.kind === "bitbucket") return bitbucket(creds, repo);
  return [];
}

async function getJson<T>(url: string, headers: Record<string, string>): Promise<T> {
  const res = await fetch(url, { headers: { accept: "application/json", "user-agent": "action-platform", ...headers }, cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`${res.status} from ${new URL(url).host}`);
  return (await res.json()) as T;
}

async function getPages<T>(url: string, headers: Record<string, string>, max = 20): Promise<T[]> {
  const out: T[] = [];
  for (let page = 1; page <= max; page++) {
    const sep = url.includes("?") ? "&" : "?";
    const rows = await getJson<T[]>(`${url}${sep}per_page=100&page=${page}`, headers);
    out.push(...rows);
    if (rows.length < 100) break;
  }
  return out;
}

async function github(creds: Credentials, repo: string): Promise<Remote[]> {
  const api = creds.base_url?.replace(/\/$/, "") || "https://api.github.com";
  type R = { tag_name: string; name: string | null; body: string | null; html_url: string; author?: { login: string }; target_commitish?: string; prerelease: boolean; draft: boolean; published_at: string | null; created_at: string };
  const rows = await getPages<R>(`${api}/repos/${repo}/releases`, { authorization: `Bearer ${creds.token}`, "x-github-api-version": "2022-11-28" });
  return rows.map((r) => ({
    tag: r.tag_name,
    name: r.name,
    body: r.body,
    url: r.html_url,
    author: r.author?.login ?? null,
    sha: null,
    prerelease: r.prerelease,
    draft: r.draft,
    publishedAt: r.published_at ? new Date(r.published_at) : new Date(r.created_at),
    source: "github",
  }));
}

async function gitlab(creds: Credentials, repo: string): Promise<Remote[]> {
  const base = creds.base_url?.replace(/\/$/, "") || "https://gitlab.com";
  type R = { tag_name: string; name: string | null; description: string | null; _links?: { self?: string }; author?: { username: string }; commit?: { id: string }; upcoming_release: boolean; released_at: string | null; created_at: string };
  const rows = await getPages<R>(`${base}/api/v4/projects/${encodeURIComponent(repo)}/releases`, { authorization: `Bearer ${creds.token}` });
  return rows.map((r) => ({
    tag: r.tag_name,
    name: r.name,
    body: r.description,
    url: r._links?.self ?? `${base}/${repo}/-/releases/${r.tag_name}`,
    author: r.author?.username ?? null,
    sha: r.commit?.id?.slice(0, 7) ?? null,
    prerelease: r.upcoming_release || /-rc\./.test(r.tag_name),
    draft: false,
    publishedAt: r.released_at ? new Date(r.released_at) : new Date(r.created_at),
    source: "gitlab",
  }));
}

async function bitbucket(creds: Credentials, repo: string): Promise<Remote[]> {
  const auth = creds.username ? `Basic ${Buffer.from(`${creds.username}:${creds.token}`).toString("base64")}` : `Bearer ${creds.token}`;
  type V = { name: string; message?: string; target?: { hash: string; date: string; author?: { user?: { display_name: string } } }; links?: { html?: { href: string } } };
  type R = { values: V[]; next?: string };
  const values: V[] = [];
  let next: string | undefined = `https://api.bitbucket.org/2.0/repositories/${repo}/refs/tags?sort=-target.date&pagelen=100`;
  while (next) {
    const data: R = await getJson<R>(next, { authorization: auth });
    values.push(...data.values);
    next = data.next;
  }
  return values.map((r) => ({
    tag: r.name,
    name: r.name,
    body: r.message ?? null,
    url: r.links?.html?.href ?? `https://bitbucket.org/${repo}/src/${r.name}/`,
    author: r.target?.author?.user?.display_name ?? null,
    sha: r.target?.hash?.slice(0, 7) ?? null,
    prerelease: /-rc\./.test(r.name),
    draft: false,
    publishedAt: r.target?.date ? new Date(r.target.date) : null,
    source: "bitbucket",
  }));
}
