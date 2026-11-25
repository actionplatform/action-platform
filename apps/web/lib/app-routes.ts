export type AppTab = { tab: string; label: string; exact?: boolean };

export function appBase(projectId: string, appId: string): string {
  return `/projects/${projectId}/apps/${appId}`;
}

export const APP_SETTINGS_PAGES: AppTab[] = [
  { tab: "settings", label: "General", exact: true },
  { tab: "settings/scopes", label: "Scopes" },
  { tab: "settings/configuration", label: "Configuration" },
  { tab: "settings/ci", label: "CI" },
];

export function appPath(projectId: string, appId: string, tab: string): string {
  return tab ? `${appBase(projectId, appId)}/${tab}` : appBase(projectId, appId);
}

const APP = "/projects/:project/apps/:app";

export const APP_REDIRECTS: { source: string; destination: string; permanent: boolean }[] = [
  { source: `${APP}/ci/connect`, destination: `${APP}/settings/ci`, permanent: true },
  { source: `${APP}/ci`, destination: `${APP}/activity?kind=ci_run`, permanent: true },
  { source: `${APP}/scopes`, destination: `${APP}/settings/scopes`, permanent: true },
  { source: `${APP}/scopes/:path+`, destination: `${APP}/settings/scopes/:path+`, permanent: true },
  { source: `${APP}/configuration`, destination: `${APP}/settings/configuration`, permanent: true },
  { source: `${APP}/activity/new`, destination: `${APP}/pull-requests/new`, permanent: true },
];
