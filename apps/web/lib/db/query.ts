import type { PostgresJsDatabase } from "drizzle-orm/postgres-js";
import { type Connection, getConnection } from "./index";
import type * as pg from "./schema/pg";

export type Db = PostgresJsDatabase<typeof pg>;
export type Schema = typeof pg;

export async function q(): Promise<{ db: Db; t: Schema }> {
  const conn: Connection = await getConnection();
  return { db: conn.db as unknown as Db, t: conn.schema as unknown as Schema };
}

export function newId(): string {
  return crypto.randomUUID();
}
