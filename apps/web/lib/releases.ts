import { type ReleaseRow, v1 } from "./v1";

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

export function storedRelease(r: ReleaseRow, appId: string): StoredRelease {
  return { id: r.id, appId, tag: r.tag, name: r.name ?? null, body: r.body ?? null, url: r.url ?? null, author: r.author ?? null, sha: r.sha ?? null, prerelease: r.prerelease, draft: r.draft, publishedAt: r.published_at ? new Date(r.published_at) : null, source: r.source, syncedAt: new Date(r.synced_at) };
}

export async function releasesOf(projectId: string, appId: string): Promise<StoredRelease[]> {
  return (await v1.imports(projectId, appId)).releases.map((r) => storedRelease(r, appId));
}
