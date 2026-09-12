// The three drizzle dialects expose the same query-builder surface at
// runtime (select / insert / update / delete / where / eq…) but distinct
// TypeScript types. This narrows every connection to the pg shape so the
// data layer is written once. Only the cross-dialect subset is used: no
// `.returning()`, ids generated in code.
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
