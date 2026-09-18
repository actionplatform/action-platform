import type { Schemas } from "./api";
import { type ReleaseRow, v1 } from "./v1";

export type Verdict = "ok" | "blocked" | "pending";
export type ReadinessRow = Schemas["ReadinessRow"];
export type ReadinessCheck = Schemas["ReadinessCheck"];

export type StoredRelease = {
  id: string;
  appId: string;
  tag: string;
  component: string;
  version: string;
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
  readiness: Record<string, Verdict>;
};

export function storedRelease(r: ReleaseRow, appId: string): StoredRelease {
  return { id: r.id, appId, tag: r.tag, component: r.component ?? "", version: r.version ?? "", name: r.name ?? null, body: r.body ?? null, url: r.url ?? null, author: r.author ?? null, sha: r.sha ?? null, prerelease: r.prerelease, draft: r.draft, publishedAt: r.published_at ? new Date(r.published_at) : null, source: r.source, syncedAt: new Date(r.synced_at), readiness: (r.readiness ?? {}) as Record<string, Verdict> };
}

export async function releasesOf(projectId: string, appId: string): Promise<StoredRelease[]> {
  return (await v1.imports(projectId, appId)).releases.map((r) => storedRelease(r, appId));
}

export async function releasesPage(projectId: string, appId: string, page: number, per: number): Promise<{ items: StoredRelease[]; total: number; page: number; per: number }> {
  const r = await v1.releasesPage(projectId, appId, page, per);
  return { items: r.items.map((x) => storedRelease(x, appId)), total: r.total, page: r.page, per: r.per };
}

export async function readinessOf(projectId: string, appId: string, tag: string): Promise<ReadinessRow[]> {
  return v1.readiness(projectId, appId, tag);
}
