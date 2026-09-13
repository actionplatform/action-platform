"use server";

import { failed } from "@/lib/result";
import { resolve } from "node:path";
import { getSetupAuth } from "@/lib/auth";
import { writeConfig } from "@/lib/config";
import { type Engine, engineOf, ensureDb, isMissingDatabase, migrateDb, pingDb } from "@/lib/db";
import { newId, q } from "@/lib/db/query";
import { setupStatus } from "@/lib/setup";
import { type HostKind } from "@/lib/source-host-kinds";
import { addHost } from "@/lib/source-hosts";
import { slugify } from "@/lib/utils";
import { DEFAULT_GIT_AUTHOR, setGitAuthor } from "@/lib/org-settings";

export type DbForm = {
  engine: Engine;
  host: string;
  port: string;
  user: string;
  password: string;
  database: string;
  ssl: boolean;
  file: string;
};

type Result = { ok: true; note?: string } | { ok: false; error: string };

function toUrl(f: DbForm): string {
  if (f.engine === "sqlite") return `sqlite:${resolve(f.file || "data/app.db")}`;

  const auth = f.password ? `${encodeURIComponent(f.user)}:${encodeURIComponent(f.password)}` : encodeURIComponent(f.user);
  const scheme = f.engine === "pg" ? "postgres" : "mysql";
  const query = f.ssl ? (f.engine === "pg" ? "?sslmode=require" : "?ssl=true") : "";

  return `${scheme}://${auth}@${f.host}:${f.port}/${f.database}${query}`;
}

function friendly(engine: Engine, e: unknown): string {
  const err = e as { code?: string; errno?: number; message?: string };
  if (isMissingDatabase(engine, e)) return "database does not exist";
  switch (err.code) {
    case "ECONNREFUSED": return "nothing is listening on that host and port";
    case "ENOTFOUND": return "host not found";
    case "28P01": case "ER_ACCESS_DENIED_ERROR": return "authentication failed";
    case "28000": return "the server refused this user (pg_hba / role)";
    case "SQLITE_CANTOPEN": return "cannot open or create that file";
    default: return err.message ?? String(e);
  }
}

export async function testDatabase(form: DbForm): Promise<Result> {
  const url = toUrl(form);
  const engine = engineOf(url);

  try {
    await pingDb(url);
    return { ok: true, note: engine === "sqlite" ? `file ok: ${url.slice(7)}` : "connection ok" };
  } catch (e) {
    if (isMissingDatabase(engine, e)) {
      return { ok: true, note: `server reachable; database "${form.database}" will be created` };
    }
    return { ok: false, error: friendly(engine, e) };
  }
}

export async function saveDatabase(form: DbForm): Promise<Result> {
  const status = await setupStatus();
  if (status.complete) return { ok: false, error: "setup already completed" };

  const url = toUrl(form);

  try {
    await ensureDb(url);
    writeConfig({ databaseUrl: url });
    await migrateDb();
    return { ok: true };
  } catch (e) {
    return { ok: false, error: friendly(engineOf(url), e) };
  }
}

export async function createAdmin(input: { name: string; email: string; password: string }): Promise<Result> {
  const status = await setupStatus();
  if (!status.dbOk) return { ok: false, error: "database is not ready" };
  if (status.hasUser) return { ok: false, error: "an account already exists — sign in instead" };

  try {
    await (await getSetupAuth()).api.signUpEmail({ body: input });
    return { ok: true };
  } catch (e) {
    return failed(e);
  }
}

export async function createFirstOrganization(input: { name: string; slug: string; gitAuthorName?: string; gitAuthorEmail?: string }): Promise<{ ok: true; orgId: string } | { ok: false; error: string }> {
  const status = await setupStatus();
  if (!status.hasUser) return { ok: false, error: "create the admin account first" };
  if (status.hasOrg) return { ok: false, error: "an organization already exists" };

  const name = input.name.trim();
  const slug = slugify(input.slug || name);
  if (!name || !slug) return { ok: false, error: "name and slug are required" };

  try {
    const { db, t } = await q();
    const [admin] = await db.select({ id: t.user.id }).from(t.user).limit(1);
    const orgId = newId();
    const now = new Date();
    await db.insert(t.organization).values({ id: orgId, name, slug, createdAt: now });
    await db.insert(t.member).values({ id: newId(), organizationId: orgId, userId: admin.id, role: "owner", createdAt: now });
    await setGitAuthor(orgId, { name: input.gitAuthorName || DEFAULT_GIT_AUTHOR.name, email: input.gitAuthorEmail || DEFAULT_GIT_AUTHOR.email });
    return { ok: true, orgId };
  } catch (e) {
    return failed(e);
  }
}

export type HostInput = { kind: HostKind; name: string; baseUrl: string; username: string; token: string; defaultOwner: string };

export async function addSetupHost(orgId: string, input: HostInput): Promise<Result> {
  const status = await setupStatus();
  if (!status.hasOrg) return { ok: false, error: "create the organization first" };

  try {
    await addHost(orgId, input);
    return { ok: true };
  } catch (e) {
    return failed(e);
  }
}
