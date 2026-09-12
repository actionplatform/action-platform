// One connection, chosen by the URL scheme the setup wizard saved:
//   postgres://user:pass@host:5432/db   mysql://user:pass@host:3306/db   sqlite:///abs/path.db
// Built on first use and rebuilt when the URL changes, so the wizard can
// switch it without a restart.
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { readConfig } from "../config";
import * as mysqlSchema from "./schema/mysql";
import * as pgSchema from "./schema/pg";
import * as sqliteSchema from "./schema/sqlite";

export type Engine = "pg" | "mysql" | "sqlite";

type PgDb = import("drizzle-orm/postgres-js").PostgresJsDatabase<typeof pgSchema>;
type MysqlDb = import("drizzle-orm/mysql2").MySql2Database<typeof mysqlSchema>;
type SqliteDb = import("drizzle-orm/libsql").LibSQLDatabase<typeof sqliteSchema>;

export type Connection =
  | { engine: "pg"; db: PgDb; schema: typeof pgSchema; close: () => Promise<void> }
  | { engine: "mysql"; db: MysqlDb; schema: typeof mysqlSchema; close: () => Promise<void> }
  | { engine: "sqlite"; db: SqliteDb; schema: typeof sqliteSchema; close: () => Promise<void> };

export function engineOf(url: string): Engine {
  if (/^postgres(ql)?:/.test(url)) return "pg";
  if (/^mysql:/.test(url)) return "mysql";
  if (/^(sqlite:|file:)/.test(url)) return "sqlite";
  throw new Error(`unsupported database url: ${url.split(":")[0]}:`);
}

function sqlitePath(url: string): string {
  return url.replace(/^sqlite:\/\/|^sqlite:|^file:/, "");
}

async function open(url: string): Promise<Connection> {
  switch (engineOf(url)) {
    case "pg": {
      const postgres = (await import("postgres")).default;
      const { drizzle } = await import("drizzle-orm/postgres-js");
      const sql = postgres(url, { max: 10 });
      return { engine: "pg", db: drizzle(sql, { schema: pgSchema }), schema: pgSchema, close: () => sql.end() };
    }
    case "mysql": {
      const mysql = await import("mysql2/promise");
      const { drizzle } = await import("drizzle-orm/mysql2");
      const pool = mysql.createPool({ uri: url, connectionLimit: 10 });
      return { engine: "mysql", db: drizzle(pool, { schema: mysqlSchema, mode: "default" }), schema: mysqlSchema, close: () => pool.end() };
    }
    case "sqlite": {
      const { createClient } = await import("@libsql/client");
      const { drizzle } = await import("drizzle-orm/libsql");
      const path = sqlitePath(url);
      mkdirSync(dirname(path), { recursive: true });
      const client = createClient({ url: `file:${path}` });
      return { engine: "sqlite", db: drizzle(client, { schema: sqliteSchema }), schema: sqliteSchema, close: async () => client.close() };
    }
  }
}

let cached: { url: string; conn: Connection } | null = null;

export async function getConnection(): Promise<Connection> {
  const url = readConfig().databaseUrl;
  if (!url) throw new Error("database is not configured");

  if (!cached || cached.url !== url) {
    if (cached) await cached.conn.close().catch(() => {});
    cached = { url, conn: await open(url) };
  }

  return cached.conn;
}

// A one-shot connection: proves the URL works, then closes.
export async function pingDb(url: string): Promise<void> {
  const conn = await open(url);
  try {
    switch (conn.engine) {
      case "pg": await conn.db.execute("select 1"); break;
      case "mysql": await conn.db.execute("select 1"); break;
      case "sqlite": await conn.db.run("select 1"); break;
    }
  } finally {
    await conn.close();
  }
}

// Servers do not create a database on connect. When the one in the URL is
// missing, connect to the maintenance db on the same server and create it.
// SQLite creates its file on open. Any other failure is left for the caller.
export async function ensureDb(url: string): Promise<{ created: boolean }> {
  const engine = engineOf(url);

  try {
    await pingDb(url);
    return { created: false };
  } catch (e) {
    if (!isMissingDatabase(engine, e)) throw e;
  }

  const target = new URL(url);
  const name = target.pathname.replace(/^\//, "");
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) throw new Error(`invalid database name: ${name}`);

  if (engine === "pg") {
    const postgres = (await import("postgres")).default;
    const admin = new URL(url);
    admin.pathname = "/postgres";
    const sql = postgres(admin.toString(), { max: 1, connect_timeout: 5 });
    try { await sql.unsafe(`create database "${name}"`); } finally { await sql.end(); }
  } else if (engine === "mysql") {
    const mysql = await import("mysql2/promise");
    const admin = new URL(url);
    admin.pathname = "/";
    const conn = await mysql.createConnection({ uri: admin.toString() });
    try { await conn.query(`create database \`${name}\``); } finally { await conn.end(); }
  }

  await pingDb(url);
  return { created: true };
}

export function isMissingDatabase(engine: Engine, e: unknown): boolean {
  const err = e as { code?: string; errno?: number };
  if (engine === "pg") return err.code === "3D000";
  if (engine === "mysql") return err.code === "ER_BAD_DB_ERROR" || err.errno === 1049;
  return false;
}

export async function migrateDb(): Promise<void> {
  const conn = await getConnection();

  switch (conn.engine) {
    case "pg": {
      const { migrate } = await import("drizzle-orm/postgres-js/migrator");
      await migrate(conn.db, { migrationsFolder: resolve("drizzle/pg") });
      break;
    }
    case "mysql": {
      const { migrate } = await import("drizzle-orm/mysql2/migrator");
      await migrate(conn.db, { migrationsFolder: resolve("drizzle/mysql") });
      break;
    }
    case "sqlite": {
      const { migrate } = await import("drizzle-orm/libsql/migrator");
      await migrate(conn.db, { migrationsFolder: resolve("drizzle/sqlite") });
      break;
    }
  }
}
