import { type PullRequestRow, v1 } from "./v1";

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

export function storedPullRequest(r: PullRequestRow, appId: string): StoredPullRequest {
  return { id: r.id, appId, number: r.number, title: r.title, url: r.url, author: r.author ?? null, head: r.head, base: r.base, state: r.state as PullRequest["state"], draft: r.draft, createdAt: r.created_at, updatedAt: r.updated_at, mergedAt: r.merged_at ?? null, source: r.source, syncedAt: new Date(r.updated_at) };
}

export async function pullRequestsOf(projectId: string, appId: string): Promise<StoredPullRequest[]> {
  return (await v1.imports(projectId, appId)).pull_requests.map((r) => storedPullRequest(r, appId));
}

export async function pullRequestsPage(projectId: string, appId: string, page: number, per: number): Promise<{ items: StoredPullRequest[]; total: number; page: number; per: number }> {
  const r = await v1.pullRequestsPage(projectId, appId, page, per);
  return { items: r.items.map((x) => storedPullRequest(x, appId)), total: r.total, page: r.page, per: r.per };
}
