import { ciOf, runOfRelease } from "@/lib/ci";
import { pageQuery } from "@/lib/page";
import { releasesPage } from "@/lib/releases";
import { loadApp } from "@/features/projects/load";
import { ReleasesTable } from "@/features/releases";

export default async function ReleasesPage({ params, searchParams }: { params: Promise<{ project: string; app: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { project, app } = await params;
  const { page, per } = pageQuery(await searchParams);
  const loaded = await loadApp(project, app);
  if (!loaded.ok) return null;
  const { view } = loaded;
  const [releases, ci] = await Promise.all([releasesPage(view.projectId, view.appId, page, per), ciOf(view.projectId, view.appId, 1, 100).catch(() => null)]);
  const canRelease = !!view.can["app.release"] && !!view.repositoryUrl;
  const runs = ci && ci.link.kind !== "none" ? Object.fromEntries(releases.items.map((r) => [r.tag, runOfRelease(ci.runs, r)])) : undefined;
  return <ReleasesTable page={releases} repositoryUrl={view.repositoryUrl} base={`/projects/${view.projectId}/apps/${view.appId}`} newHref={canRelease ? `/projects/${view.projectId}/apps/${view.appId}/releases/new` : null} ci={runs} />;
}
