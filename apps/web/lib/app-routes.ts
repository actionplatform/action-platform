export function appBase(projectId: string, appId: string): string {
  return `/projects/${projectId}/apps/${appId}`;
}

export function appPath(projectId: string, appId: string, tab: string): string {
  return tab ? `${appBase(projectId, appId)}/${tab}` : appBase(projectId, appId);
}

const APP = "/projects/:project/apps/:app";

export const APP_REDIRECTS: { source: string; destination: string; permanent: boolean }[] = [
  { source: `${APP}/settings/ci`, destination: `${APP}/settings?tab=ci`, permanent: true },
  { source: `${APP}/ci`, destination: `${APP}/activity?kind=ci_run`, permanent: true },
  { source: `${APP}/ci/connect`, destination: `${APP}/settings?tab=ci`, permanent: true },
  { source: `${APP}/settings/configuration`, destination: `${APP}/settings?tab=general`, permanent: true },
  { source: `${APP}/settings/scopes`, destination: `${APP}/scopes`, permanent: true },
  { source: `${APP}/settings/scopes/:path+`, destination: `${APP}/scopes/:path+`, permanent: true },
  { source: `${APP}/configuration`, destination: `${APP}/settings?tab=general`, permanent: true },
  { source: `${APP}/activity/new`, destination: `${APP}/pull-requests/new`, permanent: true },
];
