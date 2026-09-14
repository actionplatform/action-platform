import { authApi } from "./auth-api";

export type SetupStatus = {
  configured: boolean;
  dbOk: boolean;
  hasUser: boolean;
  hasOrg: boolean;
  complete: boolean;
  error?: string;
};

const NONE: SetupStatus = { configured: false, dbOk: false, hasUser: false, hasOrg: false, complete: false };

export async function setupStatus(): Promise<SetupStatus> {
  let status;
  try {
    status = await authApi.status();
  } catch (e) {
    return { ...NONE, error: `The API is unreachable: ${(e as Error).message}` };
  }
  if (!status.configured) return { ...NONE, error: "The API has no database or auth secret. Start it with AP_DATABASE_URL and AP_AUTH_SECRET." };
  const hasUser = status.users > 0;
  const hasOrg = status.organizations > 0;
  return { configured: true, dbOk: true, hasUser, hasOrg, complete: hasUser && hasOrg };
}
