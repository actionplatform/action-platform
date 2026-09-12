import { count, sql } from "drizzle-orm";
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
let inFlight: Promise<void> | null = null;

// Concurrent first requests must not each run the migrator: two
// `CREATE TABLE IF NOT EXISTS` at once fail on Postgres. One promise per
// process, and a database-level advisory lock across processes.
async function migrateOnce(): Promise<void> {
  const url = readConfig().databaseUrl!;
  if (migrated === url) return;

  if (!inFlight) {
    inFlight = (async () => {
      try {
        await withMigrationLock(migrateDb);
        migrated = url;
      } finally {
        inFlight = null;
      }
    })();
  }

  await inFlight;
}

const LOCK_KEY = 7788_2026;

async function withMigrationLock(fn: () => Promise<void>): Promise<void> {
  const conn = await getConnection();

  if (conn.engine === "pg") {
    await conn.db.execute(sql`select pg_advisory_lock(${LOCK_KEY})`);
    try {
      await fn();
    } finally {
      await conn.db.execute(sql`select pg_advisory_unlock(${LOCK_KEY})`);
    }
    return;
  }

  if (conn.engine === "mysql") {
    await conn.db.execute(sql`select get_lock('action_platform_migrate', 60)`);
    try {
      await fn();
    } finally {
      await conn.db.execute(sql`select release_lock('action_platform_migrate')`);
    }
    return;
  }

  await fn(); // sqlite: single process, single writer
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
