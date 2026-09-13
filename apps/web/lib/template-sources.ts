import { and, asc, eq } from "drizzle-orm";
import { newId, q } from "./db/query";
import { credentialsFor, hostsOf } from "./source-hosts";
import { slugify } from "./utils";

export type TemplateSource = { id: string; organizationId: string; name: string; url: string; ref: string; sourceHostId: string | null; createdAt: Date };
export type SourceSpec = { name: string; url: string; ref: string; credentials: Awaited<ReturnType<typeof credentialsFor>> };

export async function templateSourcesOf(orgId: string): Promise<TemplateSource[]> {
  const { db, t } = await q();
  return db.select().from(t.templateSource).where(eq(t.templateSource.organizationId, orgId)).orderBy(asc(t.templateSource.createdAt));
}

export async function sourceSpecsOf(orgId: string): Promise<SourceSpec[]> {
  const rows = await templateSourcesOf(orgId);
  return Promise.all(rows.map(async (r) => ({ name: r.name, url: r.url, ref: r.ref, credentials: r.sourceHostId ? await credentialsFor(orgId, r.sourceHostId) : null })));
}

export async function sourceSpecByName(orgId: string, name: string | null): Promise<SourceSpec | null> {
  if (!name || name === "official") return null;
  const spec = (await sourceSpecsOf(orgId)).find((s) => s.name === name);
  if (!spec) throw new Error(`template source ${name} not found`);
  return spec;
}

function kindOf(url: string): string | null {
  if (url.includes("github.com")) return "github";
  if (url.includes("gitlab")) return "gitlab";
  if (url.includes("bitbucket.org")) return "bitbucket";
  return null;
}

export async function addTemplateSource(orgId: string, input: { name: string; url: string; ref: string }): Promise<TemplateSource> {
  const { db, t } = await q();
  const name = slugify(input.name.trim());
  const url = input.url.trim();
  const ref = input.ref.trim() || "main";
  if (!name) throw new Error("name is required");
  if (name === "official") throw new Error("official is reserved");
  if (!/^(https?:\/\/|git@|ssh:\/\/|file:\/\/)/.test(url)) throw new Error("enter a git url");
  const taken = await db.select({ id: t.templateSource.id }).from(t.templateSource).where(and(eq(t.templateSource.organizationId, orgId), eq(t.templateSource.name, name))).limit(1);
  if (taken.length) throw new Error(`a source named ${name} already exists`);
  const kind = kindOf(url);
  const host = kind ? (await hostsOf(orgId)).find((h) => h.kind === kind) ?? null : null;
  const row = { id: newId(), organizationId: orgId, name, url, ref, sourceHostId: host?.id ?? null, createdAt: new Date() };
  await db.insert(t.templateSource).values(row);
  return row;
}

export async function removeTemplateSource(orgId: string, id: string): Promise<void> {
  const { db, t } = await q();
  await db.delete(t.templateSource).where(and(eq(t.templateSource.id, id), eq(t.templateSource.organizationId, orgId)));
}
