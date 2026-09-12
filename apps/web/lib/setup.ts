import { count } from "drizzle-orm";
import { readConfig } from "./config";
import { getConnection, migrateDb, pingDb } from "./db";

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
  const { databaseUrl } = readConfig();
  if (!databaseUrl) return NONE;

  try {
    await pingDb(databaseUrl);
  } catch {
    return { ...NONE, configured: true, error: "The saved database is unreachable. Check the connection settings." };
  }

  // Pending migrations (first run, or a newer app over an older database)
  // are applied here, once per process. drizzle's migrator is a no-op when
  // nothing is pending.
  await migrateOnce();

  const hasUser = await countUsers();
  const hasOrg = hasUser && (await countOrgs());
  return { configured: true, dbOk: true, hasUser, hasOrg, complete: hasUser && hasOrg };
}

let migrated: string | null = null;

async function migrateOnce(): Promise<void> {
  const url = readConfig().databaseUrl!;
  if (migrated === url) return;
  await migrateDb();
  migrated = url;
}

async function countOrgs(): Promise<boolean> {
  const conn = await getConnection();
  const rows =
    conn.engine === "pg"
      ? await conn.db.select({ n: count() }).from(conn.schema.organization)
      : conn.engine === "mysql"
        ? await conn.db.select({ n: count() }).from(conn.schema.organization)
        : await conn.db.select({ n: count() }).from(conn.schema.organization);
  return rows[0].n > 0;
}

async function countUsers(): Promise<boolean> {
  const conn = await getConnection();
  // Same query on every engine; the switch only narrows the types.
  const rows =
    conn.engine === "pg"
      ? await conn.db.select({ n: count() }).from(conn.schema.user)
      : conn.engine === "mysql"
        ? await conn.db.select({ n: count() }).from(conn.schema.user)
        : await conn.db.select({ n: count() }).from(conn.schema.user);
  return rows[0].n > 0;
}
