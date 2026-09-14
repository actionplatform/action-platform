import { PROVIDER_TIMEOUT_MS } from "@/lib/timeouts";
import { and, desc, eq } from "drizzle-orm";
import { newId, q } from "./db/query";
import { type Credentials, credentialsFor } from "./source-hosts";

export type PullRequest = {
  number: number;
  title: string;
  url: string;
  author: string | null;
  head: string;
  base: string;
  state: "open" | "merged" | "closed";
  draft: boolean;
  createdAt: string;
  updatedAt: string;
  mergedAt: string | null;
};

export type StoredPullRequest = PullRequest & { id: string; appId: string; source: string; syncedAt: Date };

export async function pullRequestsOf(appId: string): Promise<StoredPullRequest[]> {
  const { db, t } = await q();
  const rows = await db.select().from(t.pullRequest).where(eq(t.pullRequest.appId, appId)).orderBy(desc(t.pullRequest.updatedAt));
  return rows.map((r) => ({ ...r, state: r.state as PullRequest["state"], createdAt: r.createdAt.toISOString(), updatedAt: r.updatedAt.toISOString(), mergedAt: r.mergedAt ? r.mergedAt.toISOString() : null }));
}

export async function syncPullRequests(orgId: string, appId: string, sourceHostId: string | null, repo: string | null): Promise<{ ok: true; count: number } | { ok: false; error: string }> {
  if (!sourceHostId || !repo) return { ok: false, error: "no source host" };
  const creds = await credentialsFor(orgId, sourceHostId);
  if (!creds) return { ok: false, error: "no credentials" };

  let remote: PullRequest[];
  let source: string;
  try {
    if (creds.kind === "github") [remote, source] = [await github(creds, repo), "github"];
    else if (creds.kind === "gitlab") [remote, source] = [await gitlab(creds, repo), "gitlab"];
    else if (creds.kind === "bitbucket") [remote, source] = [await bitbucket(creds, repo), "bitbucket"];
    else return { ok: false, error: `pull requests are not available for ${creds.kind}` };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }

  const { db, t } = await q();
  const existing = await db.select({ id: t.pullRequest.id, number: t.pullRequest.number }).from(t.pullRequest).where(eq(t.pullRequest.appId, appId));
  const byNumber = new Map(existing.map((r) => [r.number, r.id]));
  const now = new Date();

  for (const r of remote) {
    const values = { number: r.number, title: r.title, url: r.url, author: r.author, head: r.head, base: r.base, state: r.state, draft: r.draft, createdAt: new Date(r.createdAt), updatedAt: new Date(r.updatedAt), mergedAt: r.mergedAt ? new Date(r.mergedAt) : null, source, syncedAt: now };
    const id = byNumber.get(r.number);
    if (id) {
      await db.update(t.pullRequest).set(values).where(and(eq(t.pullRequest.id, id), eq(t.pullRequest.appId, appId)));
    } else {
      await db.insert(t.pullRequest).values({ id: newId(), appId, ...values });
    }
  }

  return { ok: true, count: remote.length };
}

async function getJson<T>(url: string, headers: Record<string, string>): Promise<T> {
  const res = await fetch(url, { headers: { accept: "application/json", "user-agent": "action-platform", ...headers }, cache: "no-store", signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS) });
  if (!res.ok) throw new Error(`${res.status} from ${new URL(url).host}`);
  return (await res.json()) as T;
}

async function getPages<T>(url: string, headers: Record<string, string>, max = 10): Promise<T[]> {
  const out: T[] = [];
  for (let page = 1; page <= max; page++) {
    const rows = await getJson<T[]>(`${url}&per_page=100&page=${page}`, headers);
    out.push(...rows);
    if (rows.length < 100) break;
  }
  return out;
}

async function github(creds: Credentials, repo: string): Promise<PullRequest[]> {
  const api = creds.base_url?.replace(/\/$/, "") || "https://api.github.com";
  type R = { number: number; title: string; html_url: string; user?: { login: string }; head: { ref: string }; base: { ref: string }; state: string; draft: boolean; merged_at: string | null; created_at: string; updated_at: string };
  const rows = await getPages<R>(`${api}/repos/${repo}/pulls?state=all&sort=updated&direction=desc`, { authorization: `Bearer ${creds.token}`, "x-github-api-version": "2022-11-28" });
  return rows.map((r) => ({
    number: r.number,
    title: r.title,
    url: r.html_url,
    author: r.user?.login ?? null,
    head: r.head.ref,
    base: r.base.ref,
    state: r.merged_at ? "merged" : r.state === "open" ? "open" : "closed",
    draft: r.draft,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    mergedAt: r.merged_at,
  }));
}

async function gitlab(creds: Credentials, repo: string): Promise<PullRequest[]> {
  const base = creds.base_url?.replace(/\/$/, "") || "https://gitlab.com";
  type R = { iid: number; title: string; web_url: string; author?: { username: string }; source_branch: string; target_branch: string; state: string; draft: boolean; created_at: string; updated_at: string; merged_at: string | null };
  const rows = await getPages<R>(`${base}/api/v4/projects/${encodeURIComponent(repo)}/merge_requests?state=all&order_by=updated_at`, { authorization: `Bearer ${creds.token}` });
  return rows.map((r) => ({
    number: r.iid,
    title: r.title,
    url: r.web_url,
    author: r.author?.username ?? null,
    head: r.source_branch,
    base: r.target_branch,
    state: r.state === "merged" ? "merged" : r.state === "opened" ? "open" : "closed",
    draft: r.draft,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    mergedAt: r.merged_at,
  }));
}

async function bitbucket(creds: Credentials, repo: string): Promise<PullRequest[]> {
  const auth = creds.username ? `Basic ${Buffer.from(`${creds.username}:${creds.token}`).toString("base64")}` : `Bearer ${creds.token}`;
  type V = { id: number; title: string; links?: { html?: { href: string } }; author?: { display_name: string }; source: { branch: { name: string } }; destination: { branch: { name: string } }; state: string; created_on: string; updated_on: string };
  const values: V[] = [];
  let next: string | undefined = `https://api.bitbucket.org/2.0/repositories/${repo}/pullrequests?state=OPEN&state=MERGED&state=DECLINED&sort=-updated_on&pagelen=50`;
  while (next) {
    const data: { values: V[]; next?: string } = await getJson(next, { authorization: auth });
    values.push(...data.values);
    next = data.next;
  }
  return values.map((r) => ({
    number: r.id,
    title: r.title,
    url: r.links?.html?.href ?? `https://bitbucket.org/${repo}/pull-requests/${r.id}`,
    author: r.author?.display_name ?? null,
    head: r.source.branch.name,
    base: r.destination.branch.name,
    state: r.state === "MERGED" ? "merged" : r.state === "OPEN" ? "open" : "closed",
    draft: false,
    createdAt: r.created_on,
    updatedAt: r.updated_on,
    mergedAt: r.state === "MERGED" ? r.updated_on : null,
  }));
}
